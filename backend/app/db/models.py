from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.orchestrator.statuses import JobStatus


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_urls_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=JobStatus.PENDING.value)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    current_step: Mapped[str] = mapped_column(Text, nullable=False, default="Queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_pattern: Mapped[str | None] = mapped_column(String(120), nullable=True)
    problem_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieval_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[list[SourceDocument]] = relationship(back_populates="job", cascade="all, delete-orphan")
    evidence_items: Mapped[list[EvidenceItem]] = relationship(back_populates="job", cascade="all, delete-orphan")
    solutions: Mapped[list[GeneratedSolution]] = relationship(back_populates="job", cascade="all, delete-orphan")
    test_cases: Mapped[list[TestCase]] = relationship(back_populates="job", cascade="all, delete-orphan")
    verification_runs: Mapped[list[VerificationRun]] = relationship(back_populates="job", cascade="all, delete-orphan")
    explanations: Mapped[list[Explanation]] = relationship(back_populates="job", cascade="all, delete-orphan")
    slide_artifacts: Mapped[list[SlideArtifact]] = relationship(back_populates="job", cascade="all, delete-orphan")

    @property
    def retrieval_trace(self) -> dict[str, object] | None:
        try:
            return json.loads(self.retrieval_trace_json) if self.retrieval_trace_json else None
        except json.JSONDecodeError:
            return None


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieval_method: Mapped[str] = mapped_column(String(120), nullable=False)
    is_cache_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="sources")
    chunks: Mapped[list[SourceChunk]] = relationship(back_populates="source_document", cascade="all, delete-orphan")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    source_document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    source_chunk_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("source_chunks.id", ondelete="SET NULL"), nullable=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    support_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="evidence_items")


class GeneratedSolution(Base):
    __tablename__ = "generated_solutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    approach_type: Mapped[str] = mapped_column(String(40), nullable=False)
    algorithm_pattern: Mapped[str] = mapped_column(String(120), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    pseudocode: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    time_complexity: Mapped[str] = mapped_column(String(120), nullable=False)
    space_complexity: Mapped[str] = mapped_column(String(120), nullable=False)
    verification_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="solutions")
    verification_runs: Mapped[list[VerificationRun]] = relationship(back_populates="solution", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="test_cases")


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    solution_id: Mapped[str] = mapped_column(String(36), ForeignKey("generated_solutions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    stdout: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stderr: Mapped[str] = mapped_column(Text, nullable=False, default="")
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memory_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    test_suite_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    runtime_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sandbox_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    timeout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="verification_runs")
    solution: Mapped[GeneratedSolution] = relationship(back_populates="verification_runs")


class Explanation(Base):
    __tablename__ = "explanations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    intuition: Mapped[str] = mapped_column(Text, nullable=False)
    brute_force: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_approach: Mapped[str] = mapped_column(Text, nullable=False)
    dry_run: Mapped[str] = mapped_column(Text, nullable=False)
    pitfalls: Mapped[str] = mapped_column(Text, nullable=False)
    complexity_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="explanations")


class SlideArtifact(Base):
    __tablename__ = "slide_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    markdown_path: Mapped[str] = mapped_column(Text, nullable=False)
    html_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pptx_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    job: Mapped[Job] = relationship(back_populates="slide_artifacts")


class CanonicalProblem(Base):
    __tablename__ = "canonical_problems"
    __table_args__ = (
        UniqueConstraint("statement_hash", name="uq_canonical_problem_statement_hash"),
        UniqueConstraint("source_platform", "source_problem_id", name="uq_canonical_problem_source_identity"),
        Index("ix_canonical_problems_statement_hash", "statement_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_statement: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_statement: Mapped[str] = mapped_column(Text, nullable=False)
    statement_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    objective_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraint_signature_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    input_signature_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output_signature_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    algorithm_patterns_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    semantic_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    source_platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_problem_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ProblemVariant(Base):
    __tablename__ = "problem_variants"
    __table_args__ = (
        UniqueConstraint("canonical_problem_id", "statement_hash", name="uq_problem_variant_hash"),
        Index("ix_problem_variants_statement_hash", "statement_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    canonical_problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False)
    original_statement: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_statement: Mapped[str] = mapped_column(Text, nullable=False)
    statement_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_problem_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    origin_job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReusableSolution(Base):
    __tablename__ = "reusable_solutions"
    __table_args__ = (UniqueConstraint("canonical_problem_id", "language", "approach_type", "code_hash", name="uq_reusable_solution_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    canonical_problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False)
    approach_type: Mapped[str] = mapped_column(String(40), nullable=False)
    algorithm_pattern: Mapped[str] = mapped_column(String(120), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    pseudocode: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    time_complexity: Mapped[str] = mapped_column(String(120), nullable=False)
    space_complexity: Mapped[str] = mapped_column(String(120), nullable=False)
    input_contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNVERIFIED")
    verification_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_version: Mapped[str] = mapped_column(String(40), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_license: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    promoted_from_job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ReusableTestCase(Base):
    __tablename__ = "reusable_test_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    canonical_problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False)
    reusable_solution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("reusable_solutions.id", ondelete="CASCADE"), nullable=True)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String(40), nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    is_asserting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (UniqueConstraint("canonical_problem_id", "url", name="uq_knowledge_source_url"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    canonical_problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    external_problem_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    retrieval_method: Mapped[str] = mapped_column(String(120), nullable=False)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_full_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("knowledge_source_id", "chunk_index", name="uq_knowledge_chunk_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    knowledge_source_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    canonical_problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(40), nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProblemMatch(Base):
    __tablename__ = "problem_matches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_canonical_problem_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("canonical_problems.id", ondelete="SET NULL"), nullable=True)
    match_type: Mapped[str] = mapped_column(String(40), nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lexical_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    constraint_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    io_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    objective_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contradictions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    decision_reason_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExternalIngestionRun(Base):
    __tablename__ = "external_ingestion_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(80), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
