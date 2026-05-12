from pathlib import Path
from typing import Any

from .config import Config
from .llm import LLMClient
from .artifacts.writer import ArtifactWriter
from .documents.loader import load_documents
from .documents.chunker import chunk_by_headings


class Pipeline:
    def __init__(self, config: Config, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.writer = ArtifactWriter(config.artifacts_dir)

    def _load_prompt(self, filename: str) -> str:
        path = self.config.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def run_analyze(self, docs_dir: Path, ctx: dict[str, Any]) -> dict[str, Any]:
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
            output = self.llm.call(system_prompt, user_prompt)
            all_outputs.append(output)

        full_output = "\n\n---\n\n".join(all_outputs)
        self.writer.write("domain_inventory.md", full_output)
        print("[analyze] Wrote artifacts/domain_inventory.md")

        ctx["docs"] = docs
        ctx["domain_inventory"] = full_output
        return ctx

    def run_spec(self, ctx: dict[str, Any]) -> dict[str, Any]:
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

        spec_output = self.llm.call(system_prompt, user_prompt)

        yaml_block = _extract_block(spec_output, "```yaml") or spec_output
        self.writer.write("digital_twin_spec.yaml", yaml_block)
        print("[spec] Wrote artifacts/digital_twin_spec.yaml")

        ctx["spec_yaml"] = yaml_block
        ctx["scenarios_md"] = _extract_block(spec_output, "### Scenario") or ""
        ctx["invariants_md"] = _extract_block(spec_output, "### Invariant") or ""
        return ctx

    def run_design(self, ctx: dict[str, Any]) -> dict[str, Any]:
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

        design_output = self.llm.call(system_prompt, user_prompt)
        self.writer.write("digital_twin_design.md", design_output)
        print("[design] Wrote artifacts/digital_twin_design.md")

        ctx["design_md"] = design_output
        return ctx

    def run_generate(self, ctx: dict[str, Any]) -> dict[str, Any]:
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

        code_output = self.llm.call(system_prompt, user_prompt)
        code = _extract_block(code_output, "```python") or code_output

        self.writer.write_generated_code("twin.py", code, self.config.workspace_dir)
        self.writer.write("generated_twin.py", code)
        print("[generate] Wrote workspace/generated_twin/twin.py")

        ctx["generated_code"] = code
        return ctx

    def run_test(self, ctx: dict[str, Any]) -> dict[str, Any]:
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

        test_output = self.llm.call(system_prompt, user_prompt)
        test_code = _extract_block(test_output, "```python") or test_output

        self.writer.write_generated_code("test_twin.py", test_code, self.config.workspace_dir)
        print("[test] Wrote workspace/generated_twin/test_twin.py")

        ctx["test_code"] = test_code
        return ctx

    def run_review(self, ctx: dict[str, Any]) -> dict[str, Any]:
        print("[review] Reviewing generated code...")

        spec_yaml = ctx.get("spec_yaml", "")
        generated_code = ctx.get("generated_code", "")

        system_prompt = self._load_prompt("06_reviewer.md")
        user_prompt = (
            "Review the following digital twin implementation against the spec.\n\n"
            f"## Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
            f"## Generated Code\n\n```python\n{generated_code}\n```\n\n"
            "## Invariants\n\n" + ctx.get("invariants_md", "")
        )

        review_output = self.llm.call(system_prompt, user_prompt)
        self.writer.write("review_report.md", review_output)
        print("[review] Wrote artifacts/review_report.md")

        ctx["review_report"] = review_output
        return ctx

    def build_all(self, docs_dir: Path) -> dict[str, Any]:
        ctx: dict[str, Any] = {}

        print("=" * 50)
        print("[pipeline] Stage 1/6: Document Analysis")
        print("=" * 50)
        ctx = self.run_analyze(docs_dir, ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 2/6: Spec Generation")
        print("=" * 50)
        ctx = self.run_spec(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 3/6: Design Generation")
        print("=" * 50)
        ctx = self.run_design(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 4/6: Code Generation")
        print("=" * 50)
        ctx = self.run_generate(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 5/6: Test Generation")
        print("=" * 50)
        ctx = self.run_test(ctx)

        print("\n" + "=" * 50)
        print("[pipeline] Stage 6/6: Review")
        print("=" * 50)
        ctx = self.run_review(ctx)

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
