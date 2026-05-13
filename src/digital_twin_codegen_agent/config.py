import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    streaming: bool = False
    max_tokens: int = 8192
    temperature: float = 0.1

    eval_enabled: bool = True
    eval_threshold: int = 70
    eval_max_retries: int = 3

    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    prompts_dir: Path = field(default_factory=Path)
    artifacts_dir: Path = field(default_factory=Path)
    workspace_dir: Path = field(default_factory=Path)

    def __post_init__(self):
        self.prompts_dir = self.project_root / "prompts"
        self.artifacts_dir = self.project_root / "artifacts"
        self.workspace_dir = self.project_root / "workspace"


def load_config() -> Config:
    config = Config()

    config.api_key = os.getenv("OPENAI_API_KEY", "")
    config.model = os.getenv("OPENAI_MODEL", "")
    config.streaming = os.getenv("OPENAI_STREAMING", "false").lower() == "true"

    base_url = os.getenv("OPENAI_API_BASE_URL", "")
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    config.base_url = base_url

    config.eval_enabled = os.getenv("EVAL_ENABLED", "true").lower() != "false"
    config.eval_threshold = int(os.getenv("EVAL_THRESHOLD", "70"))
    config.eval_max_retries = int(os.getenv("EVAL_MAX_RETRIES", "3"))

    return config
