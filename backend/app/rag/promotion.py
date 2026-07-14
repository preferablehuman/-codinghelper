from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import CanonicalProblem, GeneratedSolution, Job, KnowledgeChunk, KnowledgeSource, ProblemVariant, ReusableSolution, ReusableTestCase, SourceChunk, SourceDocument, TestCase, VerificationRun
from app.rag.embeddings import embed_texts
from app.rag.problem_normalizer import NormalizedProblem
from app.rag.problem_signature import ProblemSignature
from app.rag.qdrant_store import QdrantStore
from app.rag.versions import VERIFICATION_VERSION
from app.retrieval.compliance import get_policy


_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization\s*:|bearer\s+[a-z0-9._-]{16,}|-----BEGIN [A-Z ]+PRIVATE KEY-----)")


@dataclass(frozen=True)
class PromotionResult:
    promoted: bool
    canonical_problem_id: str | None
    solution_ids: list[str]
    reason: str


def promote_successful_job(db: Session, job: Job, normalized: NormalizedProblem, signature: ProblemSignature, settings: Settings, canonical_problem_id: str | None = None) -> PromotionResult:
    if not settings.rag_promote_successful_runs or job.status not in {"COMPLETED", "PROMOTING_KNOWLEDGE"}:
        return PromotionResult(False, None, [], "Promotion disabled or job incomplete")
    asserting_tests = list(db.scalars(select(TestCase).where(TestCase.job_id == job.id, TestCase.expected_output.is_not(None))).all())
    if len(asserting_tests) < settings.rag_min_asserting_tests:
        return PromotionResult(False, None, [], "Insufficient asserting tests")
    try:
        lock_key = int(normalized.statement_hash[:15], 16)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    except Exception:
        # Non-PostgreSQL unit tests cannot provide advisory locks.
        db.rollback()
    canonical = db.get(CanonicalProblem, canonical_problem_id) if canonical_problem_id else db.scalars(select(CanonicalProblem).where(CanonicalProblem.statement_hash == normalized.statement_hash)).first()
    if canonical is None:
        canonical = CanonicalProblem(
            title=job.title or normalized.extracted_title,
            canonical_statement=job.problem_text,
            normalized_statement=normalized.normalized_text,
            statement_hash=normalized.statement_hash,
            objective_signature=signature.objective,
            constraint_signature_json=json.dumps(signature.constraints),
            input_signature_json=json.dumps(signature.io_contract),
            output_signature_json=json.dumps({"requirement": signature.output_requirement}),
            algorithm_patterns_json=json.dumps([job.detected_pattern] if job.detected_pattern else []),
            semantic_flags_json=signature.semantic_flags.model_dump_json(),
            source_platform=normalized.source_platform,
            source_problem_id=normalized.source_problem_id,
            status="ACTIVE",
        )
        db.add(canonical)
        db.flush()
    variant = db.scalars(select(ProblemVariant).where(ProblemVariant.canonical_problem_id == canonical.id, ProblemVariant.statement_hash == normalized.statement_hash)).first()
    if variant is None:
        variant = ProblemVariant(
            canonical_problem_id=canonical.id,
            original_statement=job.problem_text,
            normalized_statement=normalized.normalized_text,
            statement_hash=normalized.statement_hash,
            source_platform=normalized.source_platform,
            source_problem_id=normalized.source_problem_id,
            origin="SUCCESSFUL_JOB",
            origin_job_id=job.id,
        )
        db.add(variant)
        db.flush()

    promoted_ids: list[str] = []
    solutions = db.scalars(select(GeneratedSolution).where(GeneratedSolution.job_id == job.id)).all()
    for solution in solutions:
        verification = db.scalars(
            select(VerificationRun)
            .where(VerificationRun.solution_id == solution.id, VerificationRun.status == "PASSED", VerificationRun.failed_count == 0)
            .order_by(VerificationRun.created_at.desc())
        ).first()
        code_hash = hashlib.sha256(solution.code.encode("utf-8")).hexdigest()
        if verification is None or verification.code_hash not in (None, code_hash) or _SECRET_PATTERN.search(solution.code):
            continue
        reusable = db.scalars(
            select(ReusableSolution).where(
                ReusableSolution.canonical_problem_id == canonical.id,
                ReusableSolution.language == job.language,
                ReusableSolution.approach_type == solution.approach_type,
                ReusableSolution.code_hash == code_hash,
            )
        ).first()
        if reusable is None:
            reusable = ReusableSolution(
                canonical_problem_id=canonical.id,
                language=job.language,
                approach_type=solution.approach_type,
                algorithm_pattern=solution.algorithm_pattern,
                explanation=solution.explanation,
                pseudocode=solution.pseudocode,
                code=solution.code,
                code_hash=code_hash,
                time_complexity=solution.time_complexity,
                space_complexity=solution.space_complexity,
                input_contract_hash=_contract_hash(signature),
                verification_status="VERIFIED",
                verification_confidence=min(1.0, verification.passed_count / max(settings.rag_min_asserting_tests, 1)),
                verification_version=verification.verification_version or VERIFICATION_VERSION,
                source_kind="GENERATED_VERIFIED",
                promoted_from_job_id=job.id,
            )
            db.add(reusable)
            db.flush()
        promoted_ids.append(reusable.id)
        existing_tests = db.scalars(select(ReusableTestCase).where(ReusableTestCase.reusable_solution_id == reusable.id)).all()
        existing = {(test.input_data, test.expected_output) for test in existing_tests}
        for test in asserting_tests:
            key = (test.input_data, test.expected_output)
            if key not in existing:
                db.add(ReusableTestCase(canonical_problem_id=canonical.id, reusable_solution_id=reusable.id, input_data=test.input_data, expected_output=test.expected_output, test_type=test.test_type, origin="GENERATED", is_asserting=True))
    if not promoted_ids:
        db.rollback()
        return PromotionResult(False, None, [], "No independently verified solution variants")
    knowledge_chunks: list[KnowledgeChunk] = []
    source_rows = db.scalars(select(SourceDocument).where(SourceDocument.job_id == job.id)).all()
    for source in source_rows:
        policy = get_policy(source.source_name)
        if not policy.allow_snippets and not policy.allow_full_text:
            continue
        knowledge_source = db.scalars(select(KnowledgeSource).where(KnowledgeSource.canonical_problem_id == canonical.id, KnowledgeSource.url == source.url)).first()
        if knowledge_source is None:
            knowledge_source = KnowledgeSource(
                canonical_problem_id=canonical.id, title=source.title, url=source.url,
                source_name=source.source_name, source_tier=source.source_tier,
                source_kind="TEACHING_REFERENCE", retrieval_method=source.retrieval_method,
                license_note=source.license_note, attribution=source.url if policy.require_attribution else None,
                allow_full_text=policy.allow_full_text, content_hash=source.content_hash,
            )
            db.add(knowledge_source)
            db.flush()
        chunks = db.scalars(select(SourceChunk).where(SourceChunk.source_document_id == source.id)).all()
        existing_indices = set(db.scalars(select(KnowledgeChunk.chunk_index).where(KnowledgeChunk.knowledge_source_id == knowledge_source.id)).all())
        for chunk in chunks:
            if chunk.chunk_index in existing_indices:
                continue
            text_value = chunk.chunk_text[: policy.max_chars_to_store]
            knowledge_chunk = KnowledgeChunk(
                knowledge_source_id=knowledge_source.id, canonical_problem_id=canonical.id,
                chunk_index=chunk.chunk_index, chunk_text=text_value,
                chunk_type="TEACHING_REFERENCE",
            )
            db.add(knowledge_chunk)
            db.flush()
            knowledge_chunks.append(knowledge_chunk)
    db.commit()
    vectors = embed_texts([normalized.normalized_text], settings.embedding_model_name, allow_remote_download=settings.embedding_allow_remote_download, cache_dir=settings.embedding_cache_dir)
    if vectors:
        point_id = QdrantStore().upsert_problem_variant(vectors[0], {
            "canonical_problem_id": canonical.id,
            "problem_variant_id": variant.id,
            "statement_hash": normalized.statement_hash,
            "source_platform": normalized.source_platform,
            "source_problem_id": normalized.source_problem_id,
            "selected_pattern": job.detected_pattern,
            "semantic_flags": signature.semantic_flags.model_dump(),
            "status": "ACTIVE",
        }, variant.qdrant_point_id)
        if point_id:
            variant.qdrant_point_id = point_id
            db.add(variant)
            db.commit()
    if knowledge_chunks:
        chunk_vectors = embed_texts([chunk.chunk_text for chunk in knowledge_chunks], settings.embedding_model_name, allow_remote_download=settings.embedding_allow_remote_download, cache_dir=settings.embedding_cache_dir)
        knowledge_source_map = {source.id: source for source in db.scalars(select(KnowledgeSource).where(KnowledgeSource.id.in_({chunk.knowledge_source_id for chunk in knowledge_chunks}))).all()}
        payloads = [{
            "knowledge_chunk_id": chunk.id,
            "knowledge_source_id": chunk.knowledge_source_id,
            "canonical_problem_id": chunk.canonical_problem_id,
            "chunk_type": chunk.chunk_type,
            "source_name": knowledge_source_map[chunk.knowledge_source_id].source_name,
            "source_tier": knowledge_source_map[chunk.knowledge_source_id].source_tier,
        } for chunk in knowledge_chunks]
        point_ids = QdrantStore().upsert_knowledge_chunks(chunk_vectors, payloads)
        for chunk, point_id in zip(knowledge_chunks, point_ids, strict=False):
            if point_id:
                chunk.qdrant_point_id = point_id
                db.add(chunk)
        db.commit()
    return PromotionResult(True, canonical.id, promoted_ids, "Verified job promoted")


def _contract_hash(signature: ProblemSignature) -> str:
    payload = json.dumps({"io": signature.io_contract, "output": signature.output_requirement, "flags": signature.semantic_flags.model_dump()}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
