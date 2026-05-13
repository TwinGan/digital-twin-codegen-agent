import re
import time
from dataclasses import dataclass, field

from .artifacts.writer import ArtifactWriter
from .config import Config
from .llm import LLMClient


@dataclass
class EvaluationResult:
    passed: bool
    score: int
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw_response: str = ""


class Evaluator:
    def __init__(self, config: Config, llm: LLMClient):
        self.config = config
        self.llm = llm
        self.writer = ArtifactWriter(config.artifacts_dir)

    def evaluate(self, stage_name: str, input_text: str, output_text: str, attempt: int) -> EvaluationResult:
        prompt_path = self.config.prompts_dir / "evaluate.md"
        if not prompt_path.exists():
            return EvaluationResult(passed=True, score=100, issues=[], suggestions=[])

        system_prompt = prompt_path.read_text(encoding="utf-8")

        user_prompt = (
            f"## Stage: {stage_name}\n\n"
            f"## Input\n\n{input_text[:16000]}\n\n"
            f"## Generated Output\n\n{output_text}\n\n"
            "Evaluate the output against the input. "
            "Output your assessment in the exact format specified."
        )

        response = self.llm.call(system_prompt, user_prompt)
        ts = int(time.time())
        self.writer.write(f"evaluations/{stage_name}_attempt{attempt}_{ts}.md", response)

        return self._parse_response(response)

    def _parse_response(self, response: str) -> EvaluationResult:
        result = EvaluationResult(passed=False, score=0, raw_response=response)
        score_match = re.search(r"SCORE:\s*(\d+)", response)
        if score_match:
            result.score = int(score_match.group(1))

        pass_match = re.search(r"PASS:\s*(YES|NO)", response)
        if pass_match:
            result.passed = pass_match.group(1) == "YES"

        if not pass_match and result.score >= 60:
            result.passed = True

        issues_section = re.search(r"ISSUES:\s*\n(.*?)(?:SUGGESTIONS|$)", response, re.DOTALL)
        if issues_section:
            result.issues = [
                line.strip("- *") for line in issues_section.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        suggestions_section = re.search(r"SUGGESTIONS:\s*\n(.*?)$", response, re.DOTALL)
        if suggestions_section:
            result.suggestions = [
                line.strip("- *") for line in suggestions_section.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        return result
