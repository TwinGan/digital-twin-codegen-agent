from pathlib import Path

from ..config import Config
from ..llm import LLMClient


class CodeGenerator:
    def __init__(self, config: Config, llm: LLMClient):
        self.config = config
        self.llm = llm

    def generate(self, spec_yaml: str, design_md: str, scenarios_md: str = "", invariants_md: str = "") -> str:
        prompt_path = self.config.prompts_dir / "04_codegen.md"
        system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        user_prompt = (
            "Generate the digital twin Python implementation based on the spec and design below.\n"
            "Output ONLY valid Python code (no markdown fences, no explanations).\n"
            "The code must include:\n"
            "- A TwinEngine class with init, dispatch(command, params) method\n"
            "- Entity state management\n"
            "- Transition logic matching the spec\n"
            "- Event output for each state change\n"
            "- Explicit rejection for unsupported commands\n\n"
            f"## Digital Twin Spec\n\n```yaml\n{spec_yaml}\n```\n\n"
            f"## Architecture Design\n\n{design_md}\n\n"
            f"## Scenarios\n\n{scenarios_md}\n\n"
            f"## Invariants\n\n{invariants_md}"
        )

        code_output = self.llm.call(system_prompt, user_prompt)
        return _extract_fenced_block(code_output, "python") or code_output

    def generate_to_file(self, spec_yaml: str, design_md: str, output_path: Path,
                         scenarios_md: str = "", invariants_md: str = "") -> Path:
        code = self.generate(spec_yaml, design_md, scenarios_md, invariants_md)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")
        return output_path


def _extract_fenced_block(text: str, lang: str = "") -> str:
    marker = f"```{lang}" if lang else "```"
    parts = text.split(marker)
    if len(parts) < 2:
        return text
    block = parts[1]
    end = block.find("```")
    if end != -1:
        block = block[:end]
    return block.strip()
