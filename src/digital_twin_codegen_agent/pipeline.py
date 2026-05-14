from pathlib import Path
from typing import Any, Callable

from .config import Config
from .llm import LLMClient
from .artifacts.writer import ArtifactWriter
from .documents.loader import load_documents
from .documents.chunker import chunk_by_headings
from .evaluate import Evaluator


class Pipeline:
    def __init__(self, config: Config, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.writer = ArtifactWriter(config.artifacts_dir)
        self.evaluator = Evaluator(config, llm)

    def _load_prompt(self, filename: str) -> str:
        path = self.config.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def _build_eval_input(self, ctx: dict[str, Any], keys: list[str]) -> str:
        parts: list[str] = []
        for key in keys:
            val = ctx.get(key, "")
            if isinstance(val, dict):
                lines = []
                for k, v in val.items():
                    lines.append(f"### {k}\n{str(v)[:2000]}")
                val = "\n".join(lines)
            if val:
                parts.append(f"### {key}\n\n{str(val)[:10000]}")
        return "\n\n".join(parts)

    def _run_with_evaluation(
        self,
        stage_name: str,
        run_fn: Callable[[dict[str, Any], str], dict[str, Any]],
        ctx: dict[str, Any],
        input_keys: list[str],
        output_key: str,
        polish_hints: str = "",
    ) -> dict[str, Any]:
        if not self.config.eval_enabled:
            return run_fn(ctx, "")

        for attempt in range(1, self.config.eval_max_retries + 1):
            label = f"[{stage_name}]" if attempt == 1 else f"[{stage_name}:retry {attempt}/{self.config.eval_max_retries}]"
            print(f"{label} Generating...")

            ctx = run_fn(ctx, polish_hints)
            output = ctx.get(output_key, "")

            eval_input = self._build_eval_input(ctx, input_keys)
            if not eval_input:
                print(f"[eval:{stage_name}] No input for evaluation, skipping.")
                break

            result = self.evaluator.evaluate(stage_name, eval_input, str(output), attempt)
            print(f"[eval:{stage_name}] Score: {result.score}/100 {'PASS' if result.passed else 'FAIL'}")

            if result.passed:
                break

            if attempt < self.config.eval_max_retries:
                concrete = _filter_suggestions(result.suggestions)
                if concrete:
                    polish_hints = (
                        f"Previous attempt scored {result.score}/100. Please fix these issues:\n"
                        + "\n".join(f"- {s}" for s in concrete)
                    )
                    print(f"[eval:{stage_name}] Retrying with {len(concrete)} suggestions...")
                else:
                    polish_hints = (
                        f"Previous attempt scored {result.score}/100. "
                        "Please review and improve the output."
                    )
                    print(f"[eval:{stage_name}] Retrying with general improvement hint...")
            else:
                print(f"[eval:{stage_name}] Max retries reached. Proceeding with current output.")

        return ctx

    # ---- Stage 1: Analyze ----

    def run_analyze(self, docs_dir: Path, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[analyze] Loading documents...")
            docs = load_documents(docs_dir)
            if not docs:
                raise RuntimeError(f"No .md/.txt files found in {docs_dir}")
            print(f"[analyze] Loaded {len(docs)} document(s): {list(docs.keys())}")

            combined = ""
            for name, content in docs.items():
                combined += f"\n## File: {name}\n\n{content}\n"

            chunks = chunk_by_headings(combined)
            print(f"[analyze] Split into {len(chunks)} chunk(s)")

            all_outputs: list[str] = []
            system_prompt = self._load_prompt("01_document_analyzer.md")

            for i, chunk in enumerate(chunks, 1):
                print(f"[analyze] Processing chunk {i}/{len(chunks)}...")
                user_prompt = f"Analyze the following PRD/design documents and extract domain knowledge:\n\n{chunk}"
                if polish_hints:
                    user_prompt += f"\n\n{polish_hints}"
                output = self.llm.call(system_prompt, user_prompt)
                all_outputs.append(output)

            full_output = "\n\n---\n\n".join(all_outputs)
            self.writer.write("domain_inventory.md", full_output)
            print("[analyze] Wrote artifacts/domain_inventory.md")

            ctx["docs"] = docs
            ctx["domain_inventory"] = full_output
            return ctx

        return self._run_with_evaluation(
            "analyze", _run, ctx,
            input_keys=["docs"],
            output_key="domain_inventory",
        )

    # ---- Stage 2: Spec ----

    def run_spec(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[spec] Generating digital twin spec...")

            domain_inventory = ctx.get("domain_inventory", "")
            if not domain_inventory:
                raise RuntimeError("No domain_inventory found in context. Run analyze first.")

            docs_text = ""
            for name, content in ctx.get("docs", {}).items():
                docs_text += f"\n### Source: {name}\n\n{content[:3000]}\n"

            system_prompt = self._load_prompt("02_spec_generator.md")
            user_prompt = (
                "Based on the following domain inventory and source documents, "
                "generate a complete digital twin spec in YAML format:\n\n"
                f"## Domain Inventory\n\n{domain_inventory}\n\n"
                f"## Source Document Excerpts\n\n{docs_text}\n\n"
                "Output digital_twin_spec.yaml content."
            )
            if polish_hints:
                user_prompt += f"\n\n{polish_hints}"

            spec_output = self.llm.call(system_prompt, user_prompt)

            yaml_block = _extract_block(spec_output, "```yaml") or spec_output
            self.writer.write("digital_twin_spec.yaml", yaml_block)
            print("[spec] Wrote artifacts/digital_twin_spec.yaml")

            ctx["spec_yaml"] = yaml_block
            ctx["scenarios_md"] = _extract_block(spec_output, "### Scenario") or ""
            ctx["invariants_md"] = _extract_block(spec_output, "### Invariant") or ""
            return ctx

        return self._run_with_evaluation(
            "spec", _run, ctx,
            input_keys=["domain_inventory"],
            output_key="spec_yaml",
        )

    # ---- Stage 3: Design ----

    def run_design(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[design] Generating architecture design...")

            spec_yaml = ctx.get("spec_yaml", "")
            if not spec_yaml:
                raise RuntimeError("No spec_yaml found in context. Run spec first.")

            scenarios_md = ctx.get("scenarios_md", "")
            invariants_md = ctx.get("invariants_md", "")

            system_prompt = self._load_prompt("03_design_generator.md")
            user_prompt = (
                "Based on the following digital twin spec, design the architecture:\n\n"
                f"## Digital Twin Spec (YAML)\n\n```yaml\n{spec_yaml}\n```\n\n"
                f"## Scenarios\n\n{scenarios_md}\n\n"
                f"## Invariants\n\n{invariants_md}"
            )
            if polish_hints:
                user_prompt += f"\n\n{polish_hints}"

            design_output = self.llm.call(system_prompt, user_prompt)
            self.writer.write("digital_twin_design.md", design_output)
            print("[design] Wrote artifacts/digital_twin_design.md")

            ctx["design_md"] = design_output
            return ctx

        return self._run_with_evaluation(
            "design", _run, ctx,
            input_keys=["spec_yaml"],
            output_key="design_md",
        )

    # ---- Stage 4: Generate ----

    def run_generate(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[generate] Generating twin implementation...")

            spec_yaml = ctx.get("spec_yaml", "")
            design_md = ctx.get("design_md", "")

            if not spec_yaml:
                raise RuntimeError("No spec_yaml found in context.")

            system_prompt = self._load_prompt("04_codegen.md")
            user_prompt = (
                "Generate the digital twin Python implementation based on the spec and design below.\n"
                "Output ONLY valid Python code (no markdown fences, no explanations).\n\n"
                f"## Digital Twin Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
                f"## Architecture Design\n\n{design_md}\n\n"
                "## Scenarios\n\n" + ctx.get("scenarios_md", "") + "\n\n"
                "## Invariants\n\n" + ctx.get("invariants_md", "")
            )
            if polish_hints:
                user_prompt += (
                    f"\n\n## Polish Instructions\n"
                    f"Fix the following issues in your code output. "
                    f"Output ONLY the complete fixed Python code (no markdown, no explanations):\n"
                    f"{polish_hints}"
                )

            code_output = self.llm.call(system_prompt, user_prompt, max_tokens=32768)
            code = _extract_code(code_output)

            self.writer.write_generated_code("twin.py", code, self.config.workspace_dir)
            self.writer.write("generated_twin.py", code)
            print(f"[generate] Wrote workspace/generated_twin/twin.py ({len(code)} chars)")

            ctx["generated_code"] = code
            return ctx

        return self._run_with_evaluation(
            "generate", _run, ctx,
            input_keys=["spec_yaml", "design_md"],
            output_key="generated_code",
        )

    # ---- Stage 5: Test ----

    def run_test(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[test] Generating tests...")

            spec_yaml = ctx.get("spec_yaml", "")
            generated_code = ctx.get("generated_code", "")

            system_prompt = self._load_prompt("05_test_generator.md") if (
                self.config.prompts_dir / "05_test_generator.md").exists() else (
                "You are a test generation agent. Generate tests for the digital twin."
            )

            user_prompt = (
                "Generate Python test code for the digital twin below.\n\n"
                f"## Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
                f"## Twin Implementation\n\n```python\n{generated_code}\n```"
            )
            if polish_hints:
                user_prompt += (
                    f"\n\n## Polish Instructions\n"
                    f"Fix the following issues in your test code output. "
                    f"Output ONLY the complete fixed Python test code (no markdown, no explanations):\n"
                    f"{polish_hints}"
                )

            test_output = self.llm.call(system_prompt, user_prompt, max_tokens=16384)
            test_code = _extract_code(test_output)

            self.writer.write_generated_code("test_twin.py", test_code, self.config.workspace_dir)
            print("[test] Wrote workspace/generated_twin/test_twin.py")

            ctx["test_code"] = test_code
            return ctx

        return self._run_with_evaluation(
            "test", _run, ctx,
            input_keys=["spec_yaml", "generated_code"],
            output_key="test_code",
        )

    # ---- Stage 6: Review ----

    def run_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[review] Running programmatic coverage check...")

            spec_yaml = ctx.get("spec_yaml", "")
            generated_code = ctx.get("generated_code", "")

            from .review.coverage import analyze_coverage
            from .review.report import generate_report

            coverage = analyze_coverage(spec_yaml, generated_code)

            print("[review] Running LLM review...")
            system_prompt = self._load_prompt("06_reviewer.md")
            user_prompt = (
                "Review the following digital twin implementation against the spec.\n\n"
                f"## Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
                f"## Generated Code\n\n```python\n{generated_code}\n```\n\n"
                "## Invariants\n\n" + ctx.get("invariants_md", "")
            )
            if polish_hints:
                user_prompt += f"\n\n{polish_hints}"

            llm_review = self.llm.call(system_prompt, user_prompt)

            print("[review] Generating combined report...")
            report = generate_report(coverage, llm_review)
            self.writer.write("review_report.md", report.formatted)
            print(f"[review] Wrote artifacts/review_report.md ({'PASS' if report.passed else 'FAIL'})")

            ctx["review_report"] = report.formatted
            ctx["review_passed"] = report.passed
            return ctx

        return self._run_with_evaluation(
            "review", _run, ctx,
            input_keys=["spec_yaml", "generated_code", "invariants_md"],
            output_key="review_report",
        )

    # ---- Stage 7: Input Generator ----

    def run_input_generator(self, ctx: dict[str, Any]) -> dict[str, Any]:
        def _run(ctx: dict[str, Any], polish_hints: str) -> dict[str, Any]:
            print("[input-gen] Generating fuzz input module...")

            spec_yaml = ctx.get("spec_yaml", "")
            generated_code = ctx.get("generated_code", "")

            system_prompt = self._load_prompt("07_input_generator.md") if (
                self.config.prompts_dir / "07_input_generator.md").exists() else (
                "You are an input generation agent. Generate a fuzz testcase module."
            )

            user_prompt = (
                "Generate a standalone Python fuzz testcase module for the digital twin below.\n\n"
                f"## Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
                f"## Twin Implementation\n\n```python\n{generated_code}\n```"
            )
            if polish_hints:
                user_prompt += (
                    f"\n\n## Polish Instructions\n"
                    f"Fix the following issues in your module output. "
                    f"Output ONLY the complete fixed Python code (no markdown, no explanations):\n"
                    f"{polish_hints}"
                )

            fuzz_output = self.llm.call(system_prompt, user_prompt, max_tokens=32768)
            fuzz_code = _extract_code(fuzz_output)

            self.writer.write_generated_code("fuzz_testcases.py", fuzz_code, self.config.workspace_dir)
            self.writer.write("fuzz_testcases.py", fuzz_code)
            print(f"[input-gen] Wrote workspace/generated_twin/fuzz_testcases.py ({len(fuzz_code)} chars)")

            ctx["fuzz_module_code"] = fuzz_code
            return ctx

        return self._run_with_evaluation(
            "input-gen", _run, ctx,
            input_keys=["spec_yaml", "generated_code"],
            output_key="fuzz_module_code",
        )

    # ---- Build All ----

    def build_all(self, docs_dir: Path) -> dict[str, Any]:
        ctx: dict[str, Any] = {}

        print("=" * 50)
        print("[pipeline] Stage 1/7: Document Analysis")
        print("=" * 50)
        ctx = self.run_analyze(docs_dir, ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 2/7: Spec Generation")
        print("=" * 50)
        ctx = self.run_spec(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 3/7: Design Generation")
        print("=" * 50)
        ctx = self.run_design(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 4/7: Code Generation")
        print("=" * 50)
        ctx = self.run_generate(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 5/7: Test Generation")
        print("=" * 50)
        ctx = self.run_test(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 6/7: Review")
        print("=" * 50)
        ctx = self.run_review(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 7/7: Fuzz Input Generation")
        print("=" * 50)
        ctx = self.run_input_generator(ctx)

        print("\n[pipeline] Done. All artifacts written to artifacts/ and workspace/")
        return ctx


def _extract_block(text: str, marker: str) -> str:
    parts = text.split(marker)
    if len(parts) < 2:
        return ""
    block = parts[1]
    end = block.find("```")
    if end != -1:
        block = block[:end]
    return block.strip()


def _extract_code(text: str) -> str:
    fenced = _extract_block(text, "```python") or _extract_block(text, "```")
    if fenced and len(fenced) > 100:
        return fenced

    lines = text.splitlines()
    code_lines: list[str] = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("class ") or stripped.startswith("def ") or stripped.startswith("import ") or stripped.startswith("from "):
            in_code = True
        if in_code:
            code_lines.append(line)

    if code_lines and len(code_lines) > 5:
        return "\n".join(code_lines)

    if text.strip().startswith("class ") or text.strip().startswith("import ") or text.strip().startswith("from "):
        return text.strip()

    return text.strip()


def _filter_suggestions(suggestions: list[str]) -> list[str]:
    vague = {"add more detail", "improve the output", "be more thorough", "better", "more complete"}
    result = []
    for s in suggestions:
        sl = s.lower().strip()
        if len(sl) < 20:
            continue
        if any(v in sl for v in vague):
            continue
        result.append(s)
    return result[:3]
