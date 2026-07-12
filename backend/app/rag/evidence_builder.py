import logging
import re

from app.db.models import SourceChunk


logger = logging.getLogger(__name__)
TEACHING_SIGNALS = ("algorithm", "approach", "invariant", "state", "complexity", "pseudocode", "implementation", "data structure", "traversal", "lookup", "update")


def _pattern_terms(pattern: str) -> set[str]:
    terms = set(pattern.lower().replace("_", " ").split())
    aliases = {
        "hash_map": {"hash", "hashing", "map", "set", "lookup"},
        "graph_bfs": {"bfs", "breadth", "queue", "distance", "layer"},
        "graph_dfs": {"dfs", "depth", "recursion", "stack", "traversal"},
        "dynamic_programming": {"dp", "state", "transition", "subproblem", "memoization"},
        "two_pointers": {"pointer", "left", "right", "scan"},
        "sliding_window": {"window", "expand", "shrink", "contiguous"},
    }
    return terms | aliases.get(pattern.lower(), set())


def _chunk_score(chunk: SourceChunk, selected_pattern: str) -> float:
    text = chunk.chunk_text.lower()
    pattern_hits = sum(1 for term in _pattern_terms(selected_pattern) if term in text)
    teaching_hits = sum(1 for term in TEACHING_SIGNALS if term in text)
    source = getattr(chunk, "source_document", None)
    tier = int(getattr(source, "source_tier", 4) or 4)
    tier_bonus = max(0, 4 - tier) * 0.03
    return min(0.96, 0.48 + min(pattern_hits, 5) * 0.07 + min(teaching_hits, 6) * 0.025 + tier_bonus)


def _teaching_excerpt(text: str, selected_pattern: str, limit: int = 300) -> str:
    cleaned = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    terms = _pattern_terms(selected_pattern) | set(TEACHING_SIGNALS)
    ranked = sorted(sentences, key=lambda sentence: sum(term in sentence.lower() for term in terms), reverse=True)
    excerpt = next((sentence for sentence in ranked if len(sentence) >= 45), cleaned)
    return excerpt[:limit].rstrip(" ,;:")


def build_claims(chunks: list[SourceChunk], selected_pattern: str) -> list[tuple[SourceChunk | None, str, float]]:
    if not chunks:
        logger.info("Building evidence fallback claim selected_pattern=%s", selected_pattern)
        return [(None, f"The selected pattern is {selected_pattern}; no external algorithm chunks were available.", 0.25)]

    ranked = sorted(chunks, key=lambda chunk: _chunk_score(chunk, selected_pattern), reverse=True)
    claims: list[tuple[SourceChunk | None, str, float]] = []
    used_sources: set[str] = set()
    for chunk in ranked:
        source_id = chunk.source_document_id
        if source_id in used_sources and len(used_sources) < 3:
            continue
        source = getattr(chunk, "source_document", None)
        title = str(getattr(source, "title", "Algorithm reference"))
        score = _chunk_score(chunk, selected_pattern)
        claim = f"{title} supports the {selected_pattern} intuition: {_teaching_excerpt(chunk.chunk_text, selected_pattern)}"
        claims.append((chunk, claim, score))
        used_sources.add(source_id)
        if len(claims) >= 6:
            break
    logger.info("Built ranked algorithm evidence selected_pattern=%s chunk_count=%s claim_count=%s", selected_pattern, len(chunks), len(claims))
    return claims
