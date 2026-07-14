from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import GeneratedSolution, Job, ReusableSolution, TestCase
from app.rag.problem_matcher import RetrievalDecision
from app.rag.problem_repository import ProblemRepository
from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import parse_json_object
from app.model_runtime.prompts import adapt_verified_solution_prompt
from app.verifier.sandbox_client import verify_code
from app.solver.code_generator import _normalize_solution_payload, format_generated_code


@dataclass(frozen=True)
class ReuseResult:
    verified: bool
    solution_rows: list[GeneratedSolution]
    tests: list[dict[str, object]]
    verification_by_solution: dict[str, dict[str, object]]


def try_exact_reuse(db: Session, job: Job, decision: RetrievalDecision) -> ReuseResult:
    if decision.route != "EXACT_REUSE" or not decision.canonical_problem_id:
        return ReuseResult(False, [], [], {})
    repository = ProblemRepository(db)
    reusable = repository.verified_solutions(decision.canonical_problem_id, job.language)
    if not reusable:
        return ReuseResult(False, [], [], {})
    reusable_tests = repository.tests_for(decision.canonical_problem_id)
    tests = [{"input": test.input_data, "expected_output": test.expected_output, "test_type": test.test_type} for test in reusable_tests if test.is_asserting]
    if not tests:
        return ReuseResult(False, [], [], {})
    rows: list[GeneratedSolution] = []
    results: dict[str, dict[str, object]] = {}
    for item in reusable:
        formatted_code = format_generated_code(item.code, job.language)
        verification = verify_code(job.language, formatted_code, tests)
        if str(verification.get("status", "")).upper() != "PASSED" or int(verification.get("failed_count", 0)):
            continue
        row = GeneratedSolution(
            job_id=job.id,
            approach_type=item.approach_type,
            algorithm_pattern=item.algorithm_pattern,
            explanation=item.explanation,
            pseudocode=item.pseudocode,
            code=formatted_code,
            time_complexity=item.time_complexity,
            space_complexity=item.space_complexity,
        )
        db.add(row)
        db.flush()
        rows.append(row)
        results[row.id] = verification
    if not rows:
        db.rollback()
        return ReuseResult(False, [], [], {})
    for test in tests:
        db.add(TestCase(job_id=job.id, input_data=str(test["input"]), expected_output=str(test["expected_output"]), test_type=str(test["test_type"])))
    db.commit()
    return ReuseResult(True, rows, tests, results)


def adapt_cross_language_solution(db: Session, job: Job, decision: RetrievalDecision, runtime: BaseModelRuntime) -> ReuseResult:
    if not decision.canonical_problem_id:
        return ReuseResult(False, [], [], {})
    repository = ProblemRepository(db)
    source_solutions = repository.verified_solutions(decision.canonical_problem_id)
    if not source_solutions:
        return ReuseResult(False, [], [], {})
    source = source_solutions[0]
    reusable_tests = repository.tests_for(decision.canonical_problem_id, source.id)
    tests = [{"input": test.input_data, "expected_output": test.expected_output, "test_type": test.test_type} for test in reusable_tests if test.is_asserting]
    if not tests:
        return ReuseResult(False, [], [], {})
    canonical = {name: getattr(source, name) for name in ("approach_type", "algorithm_pattern", "explanation", "pseudocode", "code", "time_complexity", "space_complexity", "language")}
    raw = runtime.generate(adapt_verified_solution_prompt(job.problem_text, job.language, canonical, tests), max_new_tokens=4096, json_mode=True, schema_name="solution")
    data = parse_json_object(raw)
    required = ("approach_type", "algorithm_pattern", "explanation", "pseudocode", "code", "time_complexity", "space_complexity")
    if any(not isinstance(data.get(name), str) or not str(data[name]).strip() for name in required):
        return ReuseResult(False, [], [], {})
    normalized = _normalize_solution_payload(data, source.algorithm_pattern, language=job.language)
    verification = verify_code(job.language, normalized["code"], tests)
    if str(verification.get("status", "")).upper() != "PASSED" or int(verification.get("failed_count", 0)):
        return ReuseResult(False, [], tests, {})
    row = GeneratedSolution(job_id=job.id, **normalized)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReuseResult(True, [row], tests, {row.id: verification})
