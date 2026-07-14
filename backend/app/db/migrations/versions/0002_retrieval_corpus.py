"""retrieval-first reusable corpus

Revision ID: 0002_retrieval_corpus
Revises: 0001_initial
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_retrieval_corpus"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("jobs", sa.Column("retrieval_trace_json", sa.Text(), nullable=True))
    op.add_column("generated_solutions", sa.Column("verification_status", sa.String(30), nullable=True))
    for name, type_, nullable, default in (
        ("code_hash", sa.String(64), True, None),
        ("test_suite_hash", sa.String(64), True, None),
        ("verification_version", sa.String(40), True, None),
        ("verification_mode", sa.String(40), True, None),
        ("runtime_version", sa.String(120), True, None),
        ("sandbox_version", sa.String(40), True, None),
        ("timeout_count", sa.Integer(), False, "0"),
    ):
        op.add_column("verification_runs", sa.Column(name, type_, nullable=nullable, server_default=default))

    op.create_table(
        "canonical_problems",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("canonical_statement", sa.Text(), nullable=False),
        sa.Column("normalized_statement", sa.Text(), nullable=False),
        sa.Column("statement_hash", sa.String(64), nullable=False),
        sa.Column("objective_signature", sa.Text(), nullable=True),
        sa.Column("constraint_signature_json", sa.Text(), nullable=False),
        sa.Column("input_signature_json", sa.Text(), nullable=False),
        sa.Column("output_signature_json", sa.Text(), nullable=False),
        sa.Column("algorithm_patterns_json", sa.Text(), nullable=False),
        sa.Column("semantic_flags_json", sa.Text(), nullable=False),
        sa.Column("source_platform", sa.String(80), nullable=True),
        sa.Column("source_problem_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("statement_hash", name="uq_canonical_problem_statement_hash"),
        sa.UniqueConstraint("source_platform", "source_problem_id", name="uq_canonical_problem_source_identity"),
    )
    op.create_index("ix_canonical_problems_statement_hash", "canonical_problems", ["statement_hash"])
    op.execute("""DO $$ BEGIN CREATE EXTENSION IF NOT EXISTS pg_trgm; EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'pg_trgm unavailable'; END $$""")
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_trgm') THEN CREATE INDEX ix_canonical_problems_normalized_trgm ON canonical_problems USING gin (normalized_statement gin_trgm_ops); END IF; END $$""")

    op.create_table(
        "problem_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_statement", sa.Text(), nullable=False),
        sa.Column("normalized_statement", sa.Text(), nullable=False),
        sa.Column("statement_hash", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_platform", sa.String(80), nullable=True),
        sa.Column("source_problem_id", sa.String(160), nullable=True),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("origin_job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qdrant_point_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_problem_id", "statement_hash", name="uq_problem_variant_hash"),
    )
    op.create_index("ix_problem_variants_statement_hash", "problem_variants", ["statement_hash"])
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_trgm') THEN CREATE INDEX ix_problem_variants_normalized_trgm ON problem_variants USING gin (normalized_statement gin_trgm_ops); END IF; END $$""")

    op.create_table(
        "reusable_solutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(40), nullable=False),
        sa.Column("approach_type", sa.String(40), nullable=False),
        sa.Column("algorithm_pattern", sa.String(120), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("pseudocode", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("time_complexity", sa.String(120), nullable=False),
        sa.Column("space_complexity", sa.String(120), nullable=False),
        sa.Column("input_contract_hash", sa.String(64), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("verification_confidence", sa.Float(), nullable=False),
        sa.Column("verification_version", sa.String(40), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_license", sa.Text(), nullable=True),
        sa.Column("source_attribution", sa.Text(), nullable=True),
        sa.Column("promoted_from_job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("canonical_problem_id", "language", "approach_type", "code_hash", name="uq_reusable_solution_code"),
    )
    op.create_table(
        "reusable_test_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reusable_solution_id", sa.String(36), sa.ForeignKey("reusable_solutions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("test_type", sa.String(40), nullable=False),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("is_asserting", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("source_tier", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("external_problem_id", sa.String(160), nullable=True),
        sa.Column("retrieval_method", sa.String(120), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("allow_full_text", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("canonical_problem_id", "url", name="uq_knowledge_source_url"),
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("knowledge_source_id", sa.String(36), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.String(40), nullable=False),
        sa.Column("qdrant_point_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("knowledge_source_id", "chunk_index", name="uq_knowledge_chunk_index"),
    )
    op.create_table(
        "problem_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_canonical_problem_id", sa.String(36), sa.ForeignKey("canonical_problems.id", ondelete="SET NULL"), nullable=True),
        sa.Column("match_type", sa.String(40), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("lexical_score", sa.Float(), nullable=False),
        sa.Column("constraint_score", sa.Float(), nullable=False),
        sa.Column("io_score", sa.Float(), nullable=False),
        sa.Column("objective_score", sa.Float(), nullable=False),
        sa.Column("contradictions_json", sa.Text(), nullable=False),
        sa.Column("decision_reason_json", sa.Text(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "external_ingestion_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("adapter_name", sa.String(80), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for table in ("external_ingestion_runs", "problem_matches", "knowledge_chunks", "knowledge_sources", "reusable_test_cases", "reusable_solutions", "problem_variants"):
        op.drop_table(table)
    op.execute("DROP INDEX IF EXISTS ix_canonical_problems_normalized_trgm")
    op.drop_index("ix_canonical_problems_statement_hash", table_name="canonical_problems")
    op.drop_table("canonical_problems")
    for column in ("timeout_count", "sandbox_version", "runtime_version", "verification_mode", "verification_version", "test_suite_hash", "code_hash"):
        op.drop_column("verification_runs", column)
    op.drop_column("jobs", "retrieval_trace_json")
    op.drop_column("generated_solutions", "verification_status")
