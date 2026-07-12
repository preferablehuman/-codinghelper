def chunk_text(text: str, max_chars: int = 1200, max_chunks: int = 8, overlap_chars: int = 160) -> list[str]:
    paragraphs = [" ".join(paragraph.split()) for paragraph in text.splitlines() if paragraph.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = [paragraph[index : index + max_chars] for index in range(0, len(paragraph), max_chars)] or [paragraph]
        for piece in pieces:
            candidate = f"{current}\n{piece}".strip() if current else piece
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
                if len(chunks) >= max_chunks:
                    return chunks
                overlap = current[-overlap_chars:].lstrip() if overlap_chars else ""
                current = f"{overlap}\n{piece}".strip()
            else:
                current = piece
    if current and len(chunks) < max_chunks:
        chunks.append(current)
    return chunks
