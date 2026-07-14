from __future__ import annotations

import argparse
from sqlalchemy import select

from app.config import get_settings
from app.db.models import CanonicalProblem, KnowledgeChunk, ProblemVariant
from app.db.session import SessionLocal
from app.rag.embeddings import embed_texts
from app.rag.qdrant_store import QdrantStore


def run(*, dry_run: bool) -> dict[str, int]:
    summary = {"missing_points": 0, "recreated_points": 0, "orphan_points": 0, "deleted_points": 0, "hash_mismatches": 0}
    settings = get_settings()
    store = QdrantStore()
    with SessionLocal() as db:
        variants = list(db.scalars(select(ProblemVariant)).all())
        knowledge_chunks = list(db.scalars(select(KnowledgeChunk)).all())
        missing = [variant for variant in variants if not variant.qdrant_point_id]
        missing_knowledge = [chunk for chunk in knowledge_chunks if not chunk.qdrant_point_id]
        summary["missing_points"] = len(missing) + len(missing_knowledge)
        if missing and not dry_run:
            problems = {row.id: row for row in db.scalars(select(CanonicalProblem)).all()}
            texts = [variant.normalized_statement for variant in missing]
            vectors = embed_texts(texts, settings.embedding_model_name, allow_remote_download=settings.embedding_allow_remote_download, cache_dir=settings.embedding_cache_dir)
            for variant, vector in zip(missing, vectors, strict=False):
                problem = problems.get(variant.canonical_problem_id)
                if not problem:
                    continue
                point_id = store.upsert_problem_variant(vector, {
                    "canonical_problem_id": problem.id, "problem_variant_id": variant.id,
                    "statement_hash": variant.statement_hash, "source_platform": variant.source_platform,
                    "source_problem_id": variant.source_problem_id, "status": problem.status,
                })
                if point_id:
                    variant.qdrant_point_id = point_id
                    db.add(variant)
                    summary["recreated_points"] += 1
            db.commit()
        if missing_knowledge and not dry_run:
            vectors = embed_texts([chunk.chunk_text for chunk in missing_knowledge], settings.embedding_model_name, allow_remote_download=settings.embedding_allow_remote_download, cache_dir=settings.embedding_cache_dir)
            payloads = [{"knowledge_chunk_id": chunk.id, "knowledge_source_id": chunk.knowledge_source_id, "canonical_problem_id": chunk.canonical_problem_id, "chunk_type": chunk.chunk_type} for chunk in missing_knowledge]
            point_ids = store.upsert_knowledge_chunks(vectors, payloads)
            for chunk, point_id in zip(missing_knowledge, point_ids, strict=False):
                if point_id:
                    chunk.qdrant_point_id = point_id
                    db.add(chunk)
                    summary["recreated_points"] += 1
            db.commit()
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=settings.qdrant_url)
            if client.collection_exists(settings.qdrant_problem_collection):
                points, _ = client.scroll(collection_name=settings.qdrant_problem_collection, limit=10_000, with_payload=True)
                variant_ids = {variant.id for variant in variants}
                for point in points:
                    payload = getattr(point, "payload", {}) or {}
                    variant_id = str(payload.get("problem_variant_id", ""))
                    if variant_id not in variant_ids:
                        summary["orphan_points"] += 1
                        if not dry_run:
                            store.delete_problem_variant(str(point.id))
                            summary["deleted_points"] += 1
                    else:
                        variant = next(item for item in variants if item.id == variant_id)
                        if payload.get("statement_hash") != variant.statement_hash:
                            summary["hash_mismatches"] += 1
            if client.collection_exists(settings.qdrant_knowledge_collection):
                points, _ = client.scroll(collection_name=settings.qdrant_knowledge_collection, limit=10_000, with_payload=True)
                chunk_ids = {chunk.id for chunk in knowledge_chunks}
                for point in points:
                    payload = getattr(point, "payload", {}) or {}
                    if str(payload.get("knowledge_chunk_id", "")) not in chunk_ids:
                        summary["orphan_points"] += 1
                        if not dry_run:
                            store.delete_knowledge_chunk(str(point.id))
                            summary["deleted_points"] += 1
        except Exception:
            # Qdrant is optional; PostgreSQL remains authoritative.
            pass
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile PostgreSQL corpus records with Qdrant")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = run(dry_run=args.dry_run)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
