"""Widen generated and reusable solution descriptive fields.

Revision ID: 0003_widen_solution_fields
Revises: 0002_retrieval_corpus
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_widen_solution_fields"
down_revision = "0002_retrieval_corpus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("generated_solutions", "reusable_solutions"):
        for column in ("algorithm_pattern", "time_complexity", "space_complexity"):
            op.alter_column(
                table,
                column,
                existing_type=sa.String(length=120),
                type_=sa.Text(),
                existing_nullable=False,
            )


def downgrade() -> None:
    for table in ("reusable_solutions", "generated_solutions"):
        for column in ("space_complexity", "time_complexity", "algorithm_pattern"):
            op.alter_column(
                table,
                column,
                existing_type=sa.Text(),
                type_=sa.String(length=120),
                existing_nullable=False,
                postgresql_using=f"left({column}, 120)",
            )
