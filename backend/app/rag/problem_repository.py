from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import CanonicalProblem, ProblemVariant, ReusableSolution, ReusableTestCase
from app.rag.problem_normalizer import NormalizedProblem


class ProblemRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_exact(self, normalized: NormalizedProblem) -> CanonicalProblem | None:
        if normalized.source_platform and normalized.source_problem_id:
            row = self.db.scalars(
                select(CanonicalProblem).where(
                    CanonicalProblem.status == "ACTIVE",
                    CanonicalProblem.source_platform == normalized.source_platform,
                    CanonicalProblem.source_problem_id == normalized.source_problem_id,
                )
            ).first()
            if row:
                return row
        return self.db.scalars(
            select(CanonicalProblem).where(CanonicalProblem.status == "ACTIVE", CanonicalProblem.statement_hash == normalized.statement_hash)
        ).first()

    def lexical_candidates(self, normalized_text: str, limit: int) -> list[tuple[CanonicalProblem, float]]:
        try:
            score = func.similarity(CanonicalProblem.normalized_statement, normalized_text)
            rows = self.db.execute(
                select(CanonicalProblem, score.label("score"))
                .where(CanonicalProblem.status == "ACTIVE")
                .order_by(score.desc())
                .limit(limit)
            ).all()
            return [(row[0], float(row[1] or 0.0)) for row in rows]
        except Exception:
            self.db.rollback()
            from difflib import SequenceMatcher
            rows = self.db.scalars(select(CanonicalProblem).where(CanonicalProblem.status == "ACTIVE").limit(limit * 5)).all()
            scored = [(row, SequenceMatcher(None, normalized_text, row.normalized_statement).ratio()) for row in rows]
            return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

    def verified_solutions(self, canonical_problem_id: str, language: str | None = None) -> list[ReusableSolution]:
        query = select(ReusableSolution).where(
            ReusableSolution.canonical_problem_id == canonical_problem_id,
            ReusableSolution.verification_status == "VERIFIED",
        )
        if language:
            query = query.where(func.lower(ReusableSolution.language) == language.lower())
        return list(self.db.scalars(query.order_by(ReusableSolution.verification_confidence.desc())).all())

    def tests_for(self, canonical_problem_id: str, solution_id: str | None = None) -> list[ReusableTestCase]:
        query = select(ReusableTestCase).where(ReusableTestCase.canonical_problem_id == canonical_problem_id)
        if solution_id:
            query = query.where(or_(ReusableTestCase.reusable_solution_id == solution_id, ReusableTestCase.reusable_solution_id.is_(None)))
        return list(self.db.scalars(query).all())

    def variant_for_hash(self, canonical_problem_id: str, statement_hash: str) -> ProblemVariant | None:
        return self.db.scalars(select(ProblemVariant).where(ProblemVariant.canonical_problem_id == canonical_problem_id, ProblemVariant.statement_hash == statement_hash)).first()
