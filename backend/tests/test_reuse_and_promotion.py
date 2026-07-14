from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.rag.problem_matcher import RetrievalDecision
from app.rag.reuse import try_exact_reuse
from app.rag.promotion import promote_successful_job
from app.rag.problem_normalizer import normalize_problem
from app.rag.problem_signature import deterministic_signature


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)
        if value.__class__.__name__ == "GeneratedSolution" and not value.id:
            value.id = "materialized-solution"

    def flush(self): pass
    def commit(self): pass
    def rollback(self): pass


def test_exact_reuse_reverifies_and_materializes_without_generation():
    db = FakeSession()
    job = SimpleNamespace(id="job", language="java")
    decision = RetrievalDecision("EXACT_REUSE", "canonical", "EXACT_STATEMENT", 1.0)
    solution = SimpleNamespace(
        id="reusable", approach_type="OPTIMAL", algorithm_pattern="hash_map",
        explanation="verified", pseudocode="lookup", code="class Main {}",
        time_complexity="O(n)", space_complexity="O(n)",
    )
    test = SimpleNamespace(input_data="1", expected_output="1", test_type="REGRESSION", is_asserting=True)
    repository = Mock()
    repository.verified_solutions.return_value = [solution]
    repository.tests_for.return_value = [test]
    with patch("app.rag.reuse.ProblemRepository", return_value=repository), patch("app.rag.reuse.verify_code", return_value={"status": "PASSED", "passed_count": 1, "failed_count": 0}) as verify:
        result = try_exact_reuse(db, job, decision)
    assert result.verified
    assert len(result.solution_rows) == 1
    verify.assert_called_once()


def test_failed_job_is_never_promoted():
    db = Mock()
    job = SimpleNamespace(status="FAILED")
    normalized = normalize_problem("Find a value in an array")
    settings = SimpleNamespace(rag_promote_successful_runs=True)
    result = promote_successful_job(db, job, normalized, deterministic_signature(normalized.normalized_text), settings)
    assert not result.promoted
    db.add.assert_not_called()
