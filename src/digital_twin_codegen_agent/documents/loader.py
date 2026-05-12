from pathlib import Path


def load_documents(docs_dir: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")

    for file_path in sorted(docs_dir.rglob("*")):
        if file_path.is_file() and file_path.suffix in (".md", ".txt"):
            docs[str(file_path.relative_to(docs_dir))] = file_path.read_text(encoding="utf-8")

    return docs
