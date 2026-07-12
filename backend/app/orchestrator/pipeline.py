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
from app.retrieval.source_registry import RetrievedSource, is_algorithm_source, retrieve_sources
from app.slides.slide_markdown_generator import build_slide_deck, deck_to_markdown
from app.slides.slide_renderer_client import render_slides
from app.solver.code_generator import generate_solution_variants, repair_solution, select_primary_solution
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


def _local_rag_query(problem_summary: str, selected_pattern: str, candidate_patterns: list[str], problem_text: str) -> str:
    return "\n".join(
        [
            problem_summary,
            f"Selected pattern: {selected_pattern}",
            f"Candidate patterns: {', '.join(candidate_patterns)}",
            problem_text[:1200],
        ]
    )


def _local_rag_sources(results: list[dict[str, object]], selected_pattern: str) -> list[RetrievedSource]:
    sources: list[RetrievedSource] = []
    for result in results:
        payload = result.get("payload", {})
        if not isinstance(payload, dict):
            continue
        title = str(payload.get("title") or "Local RAG source")
        url = str(payload.get("url") or f"local-rag://{result.get('id', 'chunk')}")
        text = str(payload.get("text_preview") or "")
        if not text.strip():
            continue
        source = RetrievedSource(
                title=f"Local RAG: {title}",
                url=url,
                source_name=str(payload.get("source_name") or "local_rag"),
                source_tier=int(payload.get("source_tier") or 2),
                text=text,
                retrieval_method="local_rag_reuse",
                is_cache_allowed=True,
                license_note=f"Reused from local vector store; score={float(result.get('score', 0.0)):.2f}",
            )
        payload_pattern = str(payload.get("selected_pattern") or "")
        if payload_pattern and payload_pattern != selected_pattern:
            continue
        if is_algorithm_source(source):
            sources.append(source)
    return sources


def _store_verification(db, job_id: str, solution_id: str, verification: dict[str, object]) -> None:
    result_items = [item for item in verification.get("results", []) if isinstance(item, dict)]
    execution_times = [int(item.get("execution_time_ms", 0)) for item in result_items if item.get("execution_time_ms") is not None]
    average_execution_time_ms = int(sum(execution_times) / len(execution_times)) if execution_times else 0
    db.add(
        VerificationRun(
            job_id=job_id,
            solution_id=solution_id,
            status=str(verification.get("status", "INTERNAL_ERROR")),
            stdout=json.dumps(verification.get("results", [])),
            stderr=str(verification.get("stderr", "")),
            execution_time_ms=average_execution_time_ms,
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
            job.current_step = "Connecting to the model gateway and analyzing the problem"
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
            local_query = _local_rag_query(analysis.summary, analysis.selected_pattern, analysis.candidate_patterns, job.problem_text)
            local_query_vectors = embed_texts(
                [local_query],
                settings.embedding_model_name,
                allow_remote_download=settings.embedding_allow_remote_download,
                cache_dir=settings.embedding_cache_dir,
            )
            local_results = QdrantStore().search_chunks(local_query_vectors[0] if local_query_vectors else [], limit=5, score_threshold=0.62)
            local_sources = _local_rag_sources(local_results, analysis.selected_pattern)
            retrieved_sources = retrieve_sources(job.problem_text, analysis.candidate_patterns, source_urls, local_sources=local_sources)
            logger.info(
                "Retrieved sources job_id=%s requested_url_count=%s local_count=%s retrieved_count=%s",
                job.id,
                len(source_urls),
                len(local_sources),
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
                    "selected_pattern": analysis.selected_pattern,
                    "candidate_patterns": analysis.candidate_patterns,
                    "evidence_kind": "algorithm_intuition_and_code",
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
            solution_variants = generate_solution_variants(runtime, job.language, job.problem_text, analysis.selected_pattern, evidence_text)
            solution_rows: list[GeneratedSolution] = []
            for variant in solution_variants:
                row = GeneratedSolution(job_id=job.id, **variant)
                db.add(row)
                solution_rows.append(row)
            db.commit()
            for row in solution_rows:
                db.refresh(row)
            solution_data = select_primary_solution(solution_variants)
            primary_index = solution_variants.index(solution_data)
            solution = solution_rows[primary_index]
            logger.info(
                "Generated solution variants job_id=%s primary_solution_id=%s variant_count=%s code_chars=%s pattern=%s",
                job.id,
                solution.id,
                len(solution_variants),
                len(solution.code),
                solution.algorithm_pattern,
            )

            set_job_status(db, job, JobStatus.GENERATING_TESTS)
            solution_context: dict[str, object] = {**solution_data, "approach_ladder": solution_variants}
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
                solution_context = {**solution_data, "approach_ladder": [*solution_variants, solution_data]}

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
            explanation_data = build_explanation(runtime, analysis.summary, analysis.selected_pattern, solution_context, evidence_text, verification)
            db.add(Explanation(job_id=job.id, **explanation_data))
            db.commit()
            logger.info("Generated explanation job_id=%s", job.id)

            set_job_status(db, job, JobStatus.GENERATING_SLIDES)
            source_dicts = [{"title": source.title, "url": source.url} for source in source_rows]
            deck = build_slide_deck(
                runtime,
                job.title or "Programming Problem",
                analysis.summary,
                analysis.selected_pattern,
                solution_context,
                explanation_data,
                source_dicts,
            )
            markdown = deck_to_markdown(deck)
            markdown_path = save_slide_markdown(job.id, markdown)
            rendered = render_slides(job.id, markdown, deck)
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
