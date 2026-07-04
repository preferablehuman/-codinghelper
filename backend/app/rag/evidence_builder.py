import logging

from app.db.models import SourceChunk


logger = logging.getLogger(__name__)


def build_claims(chunks: list[SourceChunk], selected_pattern: str) -> list[tuple[SourceChunk | None, str, float]]:
    if not chunks:
        logger.info("Building evidence fallback claim selected_pattern=%s", selected_pattern)
        return [(None, f"The selected pattern is {selected_pattern}; no external chunks were available.", 0.25)]
    claims: list[tuple[SourceChunk | None, str, float]] = []
    for chunk in chunks[:5]:
        preview = chunk.chunk_text[:220]
        claims.append((chunk, f"Evidence supports using {selected_pattern}: {preview}", 0.72))
    logger.info("Built evidence claims selected_pattern=%s chunk_count=%s claim_count=%s", selected_pattern, len(chunks), len(claims))
    return claims
