import re


def chunk_by_headings(content: str, max_chars: int = 60000) -> list[str]:
    sections = re.split(r"(?=^#{1,3}\s)", content, flags=re.MULTILINE)
    chunks: list[str] = []
    current_chunk = ""

    for section in sections:
        if len(current_chunk) + len(section) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk += section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [content]
