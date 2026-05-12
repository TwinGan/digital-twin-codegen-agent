from pathlib import Path


class ArtifactWriter:
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def write(self, filename: str, content: str) -> Path:
        file_path = self.artifacts_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def write_generated_code(self, filename: str, content: str, workspace_dir: Path) -> Path:
        generated_dir = workspace_dir / "generated_twin"
        generated_dir.mkdir(parents=True, exist_ok=True)
        file_path = generated_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path
