import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def cmd_build_all(args: argparse.Namespace) -> None:
    docs_dir = Path(args.docs_dir).resolve()
    print(f"[build-all] Running full pipeline on: {docs_dir}")
    print("[build-all] Stage 1: analyze  -> not yet implemented")
    print("[build-all] Stage 2: spec     -> not yet implemented")
    print("[build-all] Stage 3: design   -> not yet implemented")
    print("[build-all] Stage 4: generate -> not yet implemented")
    print("[build-all] Stage 5: test     -> not yet implemented")
    print("[build-all] Stage 6: review   -> not yet implemented")
    print("[build-all] Pipeline complete.")


def cmd_analyze(args: argparse.Namespace) -> None:
    docs_dir = Path(args.docs_dir).resolve()
    print(f"[analyze] Document analysis on: {docs_dir}")
    print("[analyze] Not yet implemented.")


def cmd_spec(args: argparse.Namespace) -> None:
    print("[spec] Spec generation from domain inventory.")
    print("[spec] Not yet implemented.")


def cmd_design(args: argparse.Namespace) -> None:
    print("[design] Design generation from spec.")
    print("[design] Not yet implemented.")


def cmd_generate(args: argparse.Namespace) -> None:
    print("[generate] Code generation from spec + design.")
    print("[generate] Not yet implemented.")


def cmd_test(args: argparse.Namespace) -> None:
    print("[test] Test generation from spec + code.")
    print("[test] Not yet implemented.")


def cmd_review(args: argparse.Namespace) -> None:
    print("[review] Review generated code against spec.")
    print("[review] Not yet implemented.")


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

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
