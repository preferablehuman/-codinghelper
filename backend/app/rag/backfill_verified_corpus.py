from __future__ import annotations

import argparse
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Job, KnowledgeChunk, ProblemVariant
from app.db.session import SessionLocal
from app.rag.problem_normalizer import normalize_problem
from app.rag.problem_signature import deterministic_signature
from app.rag.promotion import promote_successful_job
from app.rag.qdrant_store import QdrantStore


def run(*, dry_run: bool, job_id: str | None, limit: int | None, rebuild_vectors: bool) -> dict[str, int]:
    summary = {"examined": 0, "promoted": 0, "skipped": 0}
    with SessionLocal() as db:
        query = select(Job).where(Job.status == "COMPLETED").order_by(Job.completed_at.asc())
        if job_id:
            query = query.where(Job.id == job_id)
        if limit:
            query = query.limit(limit)
        jobs = list(db.scalars(query).all())
        for job in jobs:
            summary["examined"] += 1
            if dry_run:
                # Promotion performs all detailed gates; dry-run intentionally makes no writes.
                verified_solution_ids = {run.solution_id for run in job.verification_runs if run.status == "PASSED" and run.failed_count == 0}
                asserting_count = sum(test.expected_output is not None for test in job.test_cases)
                if verified_solution_ids and asserting_count >= get_settings().rag_min_asserting_tests:
                    summary["promoted"] += 1
                else:
                    summary["skipped"] += 1
                continue
            normalized = normalize_problem(job.problem_text)
            result = promote_successful_job(db, job, normalized, deterministic_signature(normalized.normalized_text), get_settings())
            summary["promoted" if result.promoted else "skipped"] += 1
        if rebuild_vectors and not dry_run:
            store = QdrantStore()
            for variant in db.scalars(select(ProblemVariant).where(ProblemVariant.qdrant_point_id.is_not(None))).all():
                store.delete_problem_variant(variant.qdrant_point_id)
                variant.qdrant_point_id = None
                db.add(variant)
            for chunk in db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.qdrant_point_id.is_not(None))).all():
                store.delete_knowledge_chunk(chunk.qdrant_point_id)
                chunk.qdrant_point_id = None
                db.add(chunk)
            db.commit()
    if rebuild_vectors and not dry_run:
        from app.rag.reconcile_qdrant import run as reconcile
        reconcile(dry_run=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote verified historical jobs into the reusable corpus")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--job-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--rebuild-vectors", action="store_true")
    args = parser.parse_args()
    summary = run(dry_run=args.dry_run, job_id=args.job_id, limit=args.limit, rebuild_vectors=args.rebuild_vectors)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
