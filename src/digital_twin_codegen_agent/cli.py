import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .config import load_config
from .llm import LLMClient
from .pipeline import Pipeline

load_dotenv()


def _build_context_from_artifacts(artifacts_dir: Path) -> dict[str, Any]:
    ctx: dict[str, Any] = {}

    domain_inv = artifacts_dir / "domain_inventory.md"
    if domain_inv.exists():
        ctx["domain_inventory"] = domain_inv.read_text(encoding="utf-8")

    spec_file = artifacts_dir / "digital_twin_spec.yaml"
    if spec_file.exists():
        ctx["spec_yaml"] = spec_file.read_text(encoding="utf-8")

    design_file = artifacts_dir / "digital_twin_design.md"
    if design_file.exists():
        ctx["design_md"] = design_file.read_text(encoding="utf-8")

    code_file = artifacts_dir / "generated_twin.py"
    if code_file.exists():
        ctx["generated_code"] = code_file.read_text(encoding="utf-8")

    return ctx


def _get_pipeline() -> Pipeline:
    cfg = load_config()
    llm = LLMClient(cfg)
    return Pipeline(cfg, llm)


def cmd_build_all(args: argparse.Namespace) -> None:
    docs_dir = Path(args.docs_dir).resolve()
    pipeline = _get_pipeline()
    ctx = pipeline.build_all(docs_dir)

    twin_path = pipeline.config.workspace_dir / "generated_twin" / "twin.py"
    if twin_path.exists():
        print("\n[cli] Running generated twin scenarios...")
        from .execution.runner import TwinRunner

        runner = TwinRunner(twin_path)
        runner.load()

        spec_yaml = ctx.get("spec_yaml", "")
        if spec_yaml:
            import yaml
            spec_data = yaml.safe_load(spec_yaml)
            scenarios = spec_data.get("scenarios", [])
            if scenarios:
                results = runner.run_all_scenarios(scenarios)
                runner.print_report(results)


def cmd_analyze(args: argparse.Namespace) -> None:
    docs_dir = Path(args.docs_dir).resolve()
    pipeline = _get_pipeline()
    pipeline.run_analyze(docs_dir, {})
    print("[analyze] Done.")


def cmd_spec(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_spec(ctx)
    print("[spec] Done.")


def cmd_design(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_design(ctx)
    print("[design] Done.")


def cmd_generate(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_generate(ctx)
    print("[generate] Done.")


def cmd_test(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_test(ctx)

    twin_path = pipeline.config.workspace_dir / "generated_twin" / "twin.py"
    if twin_path.exists():
        print("\n[cli] Running generated twin scenarios...")
        from .execution.runner import TwinRunner

        runner = TwinRunner(twin_path)
        runner.load()
        spec_yaml = ctx.get("spec_yaml", "")
        if spec_yaml:
            import yaml
            spec_data = yaml.safe_load(spec_yaml)
            scenarios = spec_data.get("scenarios", [])
            if scenarios:
                results = runner.run_all_scenarios(scenarios)
                runner.print_report(results)

    print("[test] Done.")


def cmd_review(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_review(ctx)
    print("[review] Done.")


def cmd_input_gen(args: argparse.Namespace) -> None:
    pipeline = _get_pipeline()
    ctx = _build_context_from_artifacts(pipeline.config.artifacts_dir)
    pipeline.run_input_generator(ctx)
    print("[input-gen] Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dt-codegen",
        description="Digital Twin Code Generation Agent",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_build_all = subparsers.add_parser("build-all", help="Run the full pipeline")
    parser_build_all.add_argument("docs_dir", type=str, help="Path to documents directory")
    parser_build_all.set_defaults(func=cmd_build_all)

    parser_analyze = subparsers.add_parser("analyze", help="Run document analysis")
    parser_analyze.add_argument("docs_dir", type=str, help="Path to documents directory")
    parser_analyze.set_defaults(func=cmd_analyze)

    parser_spec = subparsers.add_parser("spec", help="Generate behavior spec")
    parser_spec.set_defaults(func=cmd_spec)

    parser_design = subparsers.add_parser("design", help="Generate architecture design")
    parser_design.set_defaults(func=cmd_design)

    parser_generate = subparsers.add_parser("generate", help="Generate twin implementation")
    parser_generate.set_defaults(func=cmd_generate)

    parser_test = subparsers.add_parser("test", help="Generate tests for the twin")
    parser_test.set_defaults(func=cmd_test)

    parser_review = subparsers.add_parser("review", help="Review generated code against spec")
    parser_review.set_defaults(func=cmd_review)

    parser_input_gen = subparsers.add_parser("input-gen", help="Generate fuzz testcase module")
    parser_input_gen.set_defaults(func=cmd_input_gen)

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
