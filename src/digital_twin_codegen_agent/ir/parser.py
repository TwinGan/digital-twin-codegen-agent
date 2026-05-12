from pathlib import Path
from typing import Any

import yaml

from .schemas import TwinSpec


def parse_spec_yaml(file_path: Path) -> TwinSpec:
    raw = file_path.read_text(encoding="utf-8")
    return parse_spec_string(raw)


def parse_spec_string(content: str) -> TwinSpec:
    data: dict[str, Any] = yaml.safe_load(content)
    if data is None:
        raise ValueError("Empty or invalid YAML content")
    return TwinSpec.from_dict(data)
