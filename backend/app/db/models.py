from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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
