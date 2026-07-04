"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("problem_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=True),
        sa.Column("source_urls_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("detected_pattern", sa.String(length=120), nullable=True),
        sa.Column("problem_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_tier", sa.Integer(), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("retrieval_method", sa.String(length=120), nullable=False),
        sa.Column("is_cache_allowed", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("qdrant_point_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("source_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("support_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["source_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "generated_solutions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("approach_type", sa.String(length=40), nullable=False),
        sa.Column("algorithm_pattern", sa.String(length=120), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("pseudocode", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("time_complexity", sa.String(length=120), nullable=False),
        sa.Column("space_complexity", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("test_type", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("solution_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("memory_used_mb", sa.Integer(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["solution_id"], ["generated_solutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "explanations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("intuition", sa.Text(), nullable=False),
        sa.Column("brute_force", sa.Text(), nullable=False),
        sa.Column("optimized_approach", sa.Text(), nullable=False),
        sa.Column("dry_run", sa.Text(), nullable=False),
        sa.Column("pitfalls", sa.Text(), nullable=False),
        sa.Column("complexity_analysis", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "slide_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=False),
        sa.Column("html_path", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("pptx_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("slide_artifacts")
    op.drop_table("explanations")
    op.drop_table("verification_runs")
    op.drop_table("test_cases")
    op.drop_table("generated_solutions")
    op.drop_table("evidence_items")
    op.drop_table("source_chunks")
    op.drop_table("source_documents")
    op.drop_table("jobs")
