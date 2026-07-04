def chunk_text(text: str, max_chars: int = 900, max_chunks: int = 8) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized) and len(chunks) < max_chunks:
        chunks.append(normalized[start : start + max_chars])
        start += max_chars
    return chunks

