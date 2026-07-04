import hashlib
import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.artifacts.artifact_store import save_slide_markdown
from app.config import get_settings
from app.db.models import (
    EvidenceItem,
    Explanation,
    GeneratedSolution,
    Job,
    SlideArtifact,
    SourceChunk,
    SourceDocument,
    TestCase,
    VerificationRun,
)
from app.db.session import SessionLocal
from app.explainer.explanation_generator import build_explanation
from app.model_runtime.provider import get_model_runtime
from app.orchestrator.job_manager import set_job_status
from app.orchestrator.statuses import JobStatus
from app.rag.chunker import chunk_text
from app.rag.embeddings import embed_texts
from app.rag.evidence_builder import build_claims
from app.rag.qdrant_store import QdrantStore
from app.retrieval.source_registry import retrieve_sources
from app.slides.slide_markdown_generator import build_slide_markdown
from app.slides.slide_renderer_client import render_slides
from app.solver.code_generator import generate_solution, repair_solution
from app.solver.problem_analyzer import analyze_problem
from app.solver.test_generator import generate_tests
from app.verifier.sandbox_client import verify_code


logger = logging.getLogger(__name__)


def _format_evidence_text(
    problem_summary: str,
    selected_pattern: str,
    source_rows: list[SourceDocument],
    claims: list[tuple[SourceChunk | None, str, float]],
) -> str:
    source_lines = [f"- {source.title} ({source.source_name}, tier {source.source_tier}): {source.url}" for source in source_rows]
    claim_lines = [f"- score={score:.2f}: {claim}" for _, claim, score in claims]
    return "\n".join(
        [
            f"Problem summary: {problem_summary}",
            f"Selected pattern: {selected_pattern}",
            "Sources:",
            *(source_lines or ["- No sources available"]),
            "Evidence claims:",
            *(claim_lines or ["- No evidence claims available"]),
        ]
    )


def _verification_passed(verification: dict[str, object]) -> bool:
    return str(verification.get("status", "")).upper() == "PASSED" and int(verification.get("failed_count", 0)) == 0


def _store_verification(db, job_id: str, solution_id: str, verification: dict[str, object]) -> None:
    db.add(
        VerificationRun(
            job_id=job_id,
            solution_id=solution_id,
            status=str(verification.get("status", "INTERNAL_ERROR")),
            stdout=json.dumps(verification.get("results", [])),
            stderr=str(verification.get("stderr", "")),
            execution_time_ms=0,
            memory_used_mb=None,
            passed_count=int(verification.get("passed_count", 0)),
            failed_count=int(verification.get("failed_count", 0)),
        )
    )
    db.commit()
    logger.info(
        "Stored verification run job_id=%s solution_id=%s status=%s passed=%s failed=%s",
        job_id,
        solution_id,
        verification.get("status", "INTERNAL_ERROR"),
        verification.get("passed_count", 0),
        verification.get("failed_count", 0),
    )


def run_job_pipeline(job_id: str) -> None:
    started = time.perf_counter()
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("Job pipeline requested for missing job job_id=%s", job_id)
            return
        try:
            logger.info("Job pipeline started job_id=%s language=%s", job.id, job.language)
            set_job_status(db, job, JobStatus.ANALYZING)
            job.current_step = "Loading local model and analyzing problem"
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info("Analysis step entered model runtime job_id=%s", job.id)
            runtime = get_model_runtime()
            analysis = analyze_problem(runtime, job.problem_text, job.language)
            job.problem_summary = analysis.summary
            job.detected_pattern = analysis.selected_pattern
            db.commit()
            db.refresh(job)
            logger.info(
                "Problem analysis complete job_id=%s selected_pattern=%s candidate_count=%s edge_case_count=%s",
                job.id,
                analysis.selected_pattern,
                len(analysis.candidate_patterns),
                len(analysis.edge_cases),
            )

            set_job_status(db, job, JobStatus.RETRIEVING_SOURCES)
            source_urls = json.loads(job.source_urls_json or "[]")
            retrieved_sources = retrieve_sources(job.problem_text, analysis.candidate_patterns, source_urls)
            logger.info(
                "Retrieved sources job_id=%s requested_url_count=%s retrieved_count=%s",
                job.id,
                len(source_urls),
                len(retrieved_sources),
            )
            source_rows: list[SourceDocument] = []
            chunks: list[SourceChunk] = []
            for source in retrieved_sources[: settings.max_sources_per_job]:
                source_row = SourceDocument(
                    job_id=job.id,
                    title=source.title,
                    url=source.url,
                    source_name=source.source_name,
                    source_tier=source.source_tier,
                    license_note=source.license_note,
                    retrieval_method=source.retrieval_method,
                    is_cache_allowed=source.is_cache_allowed,
                    content_hash=hashlib.sha256(source.text.encode("utf-8")).hexdigest() if source.text else None,
                )
                db.add(source_row)
                db.flush()
                source_rows.append(source_row)
                for index, text in enumerate(chunk_text(source.text, max_chunks=settings.max_chunks_per_source)):
                    chunk = SourceChunk(
                        source_document_id=source_row.id,
                        job_id=job.id,
                        chunk_index=index,
                        chunk_text=text,
                    )
                    db.add(chunk)
                    db.flush()
                    chunks.append(chunk)
            db.commit()
            logger.info(
                "Stored source material job_id=%s source_count=%s chunk_count=%s",
                job.id,
                len(source_rows),
                len(chunks),
            )

            set_job_status(db, job, JobStatus.BUILDING_EVIDENCE)
            vectors = embed_texts(
                [chunk.chunk_text for chunk in chunks],
                settings.embedding_model_name,
                allow_remote_download=settings.embedding_allow_remote_download,
                cache_dir=settings.embedding_cache_dir,
            )
            payloads = [
                {
                    "job_id": job.id,
                    "source_document_id": chunk.source_document_id,
                    "source_name": next((source.source_name for source in source_rows if source.id == chunk.source_document_id), ""),
                    "url": next((source.url for source in source_rows if source.id == chunk.source_document_id), ""),
                    "title": next((source.title for source in source_rows if source.id == chunk.source_document_id), ""),
                    "chunk_index": chunk.chunk_index,
                    "text_preview": chunk.chunk_text[:280],
                    "source_tier": next((source.source_tier for source in source_rows if source.id == chunk.source_document_id), 4),
                }
                for chunk in chunks
            ]
            point_ids = QdrantStore().upsert_chunks(vectors, payloads)
            for chunk, point_id in zip(chunks, point_ids, strict=False):
                chunk.qdrant_point_id = point_id or None
                db.add(chunk)
            evidence_claims = build_claims(chunks, analysis.selected_pattern)
            for chunk, claim, score in evidence_claims:
                db.add(EvidenceItem(job_id=job.id, source_chunk_id=chunk.id if chunk else None, claim=claim, support_score=score))
            db.commit()
            evidence_text = _format_evidence_text(analysis.summary, analysis.selected_pattern, source_rows, evidence_claims)
            logger.info(
                "Built evidence job_id=%s vector_count=%s qdrant_point_count=%s evidence_claim_count=%s",
                job.id,
                len(vectors),
                len([point_id for point_id in point_ids if point_id]),
                len(evidence_claims),
            )

            set_job_status(db, job, JobStatus.GENERATING_SOLUTION)
            solution_data = generate_solution(runtime, job.language, job.problem_text, analysis.selected_pattern, evidence_text)
            solution = GeneratedSolution(job_id=job.id, **solution_data)
            db.add(solution)
            db.commit()
            db.refresh(solution)
            logger.info(
                "Generated solution job_id=%s solution_id=%s code_chars=%s pattern=%s",
                job.id,
                solution.id,
                len(solution.code),
                solution.algorithm_pattern,
            )

            set_job_status(db, job, JobStatus.GENERATING_TESTS)
            tests = generate_tests(runtime, job.problem_text, job.language, solution_data)
            for test in tests:
                db.add(
                    TestCase(
                        job_id=job.id,
                        input_data=test["input"],
                        expected_output=test.get("expected_output"),
                        test_type=test.get("test_type", "GENERATED"),
                    )
                )
            db.commit()
            logger.info("Generated tests job_id=%s test_count=%s", job.id, len(tests))

            set_job_status(db, job, JobStatus.VERIFYING)
            verification = verify_code(job.language, solution.code, tests)
            _store_verification(db, job.id, solution.id, verification)

            for repair_attempt in range(settings.max_repair_attempts):
                if _verification_passed(verification):
                    logger.info("Verification passed job_id=%s repair_attempts_used=%s", job.id, repair_attempt)
                    break
                set_job_status(db, job, JobStatus.REPAIRING)
                logger.warning(
                    "Verification failed; attempting repair job_id=%s attempt=%s status=%s failed=%s",
                    job.id,
                    repair_attempt + 1,
                    verification.get("status"),
                    verification.get("failed_count"),
                )
                solution_data = repair_solution(
                    runtime,
                    job.language,
                    job.problem_text,
                    evidence_text,
                    solution_data,
                    tests,
                    verification,
                )
                solution = GeneratedSolution(job_id=job.id, **solution_data)
                db.add(solution)
                db.commit()
                db.refresh(solution)

                set_job_status(db, job, JobStatus.VERIFYING)
                verification = verify_code(job.language, solution.code, tests)
                _store_verification(db, job.id, solution.id, verification)
            if not _verification_passed(verification):
                logger.warning(
                    "Verification did not pass after repairs job_id=%s final_status=%s failed=%s",
                    job.id,
                    verification.get("status"),
                    verification.get("failed_count"),
                )

            set_job_status(db, job, JobStatus.GENERATING_EXPLANATION)
            explanation_data = build_explanation(runtime, analysis.summary, analysis.selected_pattern, solution_data, evidence_text, verification)
            db.add(Explanation(job_id=job.id, **explanation_data))
            db.commit()
            logger.info("Generated explanation job_id=%s", job.id)

            set_job_status(db, job, JobStatus.GENERATING_SLIDES)
            source_dicts = [{"title": source.title, "url": source.url} for source in source_rows]
            markdown = build_slide_markdown(
                runtime,
                job.title or "Programming Problem",
                analysis.summary,
                analysis.selected_pattern,
                solution_data,
                explanation_data,
                source_dicts,
            )
            markdown_path = save_slide_markdown(job.id, markdown)
            rendered = render_slides(job.id, markdown)
            db.add(
                SlideArtifact(
                    job_id=job.id,
                    markdown_path=markdown_path,
                    html_path=rendered.get("html_path"),
                    pdf_path=rendered.get("pdf_path"),
                    pptx_path=rendered.get("pptx_path"),
                )
            )
            db.commit()
            logger.info(
                "Generated slide artifact job_id=%s markdown_chars=%s html_path=%s pptx_path=%s",
                job.id,
                len(markdown),
                rendered.get("html_path"),
                rendered.get("pptx_path"),
            )

            set_job_status(db, job, JobStatus.COMPLETED)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info("Job pipeline completed job_id=%s elapsed_ms=%s", job.id, elapsed_ms)
        except Exception as exc:
            db.rollback()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception("Job pipeline failed job_id=%s elapsed_ms=%s", job_id, elapsed_ms)
            job = db.scalars(select(Job).where(Job.id == job_id)).first()
            if job is not None:
                job.completed_at = datetime.now(timezone.utc)
                set_job_status(db, job, JobStatus.FAILED, error_message=str(exc))
