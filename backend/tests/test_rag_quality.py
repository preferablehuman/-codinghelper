from app.db.models import SourceChunk, SourceDocument
from app.rag.chunker import chunk_text
from app.rag.evidence_builder import build_claims
from app.retrieval import source_registry


def test_algorithm_registry_excludes_language_documentation(monkeypatch) -> None:
    monkeypatch.setattr(source_registry, "_fetch_source", lambda source: source)

    sources = source_registry.retrieve_sources("validate a sudoku board", ["hash_map"], [])

    assert sources
    assert all("docs.python.org" not in source.url for source in sources)
    assert all("docs.oracle.com" not in source.url for source in sources)
    assert any("hash" in f"{source.title} {source.text}".lower() for source in sources)


def test_chunker_preserves_paragraph_boundaries_with_overlap() -> None:
    text = "First paragraph explains the invariant.\n" + ("State update detail. " * 90) + "\nFinal complexity paragraph."

    chunks = chunk_text(text, max_chars=240, max_chunks=6, overlap_chars=40)

    assert 2 <= len(chunks) <= 6
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert "First paragraph" in chunks[0]


def test_evidence_builder_prefers_pattern_intuition_over_navigation_text() -> None:
    weak_source = SourceDocument(
        id="weak",
        job_id="job",
        title="Navigation",
        url="https://example.test/navigation",
        source_name="generic_web",
        source_tier=4,
        retrieval_method="test",
        is_cache_allowed=True,
    )
    strong_source = SourceDocument(
        id="strong",
        job_id="job",
        title="Hashing data structure",
        url="https://example.test/hashing",
        source_name="geeksforgeeks",
        source_tier=2,
        retrieval_method="test",
        is_cache_allowed=True,
    )
    chunks = [
        SourceChunk(id="weak-chunk", job_id="job", source_document_id="weak", chunk_index=0, chunk_text="Home archive contact categories next previous"),
        SourceChunk(
            id="strong-chunk",
            job_id="job",
            source_document_id="strong",
            chunk_index=0,
            chunk_text="A hash set stores seen values as state. Each lookup detects a duplicate in constant time on average, so one traversal replaces repeated scans.",
        ),
    ]
    chunks[0].source_document = weak_source
    chunks[1].source_document = strong_source

    claims = build_claims(chunks, "hash_map")

    assert claims[0][0] is chunks[1]
    assert "Hashing data structure" in claims[0][1]
    assert claims[0][2] > claims[-1][2]
