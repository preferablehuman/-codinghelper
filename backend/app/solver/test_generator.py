import logging
from collections import Counter
from typing import Any

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_array, parse_json_object, response_preview
from app.model_runtime.prompts import tests_prompt

VALID_TEST_TYPES = {"SAMPLE", "EDGE", "GENERATED", "RANDOM"}
logger = logging.getLogger(__name__)


def generate_tests(runtime: BaseModelRuntime, problem_text: str, language: str, solution: dict[str, str]) -> list[dict[str, str | None]]:
    logger.info("Generating tests language=%s problem_chars=%s code_chars=%s", language, len(problem_text), len(solution.get("code", "")))
    raw = runtime.generate(tests_prompt(problem_text, language, solution), max_new_tokens=2048, json_mode=True)
    try:
        data = _parse_test_payload(raw)
    except ValueError:
        logger.error("Test JSON parse failed response_preview=%s", response_preview(raw))
        raise
    tests = [_normalize_test_case(item) for item in data]
    tests = _normalize_multiple_answer_tests(problem_text, tests)
    if not tests:
        raise ValueError("Model did not generate any test cases.")
    logger.info("Test payload parsed test_count=%s test_types=%s", len(tests), sorted({test["test_type"] for test in tests}))
    return tests


def _parse_test_payload(raw: str) -> list[Any]:
    try:
        return parse_json_array(raw)
    except ValueError as array_error:
        data = parse_json_object(raw)
        for key in ("tests", "test_cases", "cases"):
            value = data.get(key)
            if isinstance(value, list):
                logger.warning("Test payload used wrapped array key=%s", key)
                return value
        if "input" in data or "expected_output" in data:
            logger.warning("Test payload used a single object; wrapping as one generated test")
            return [data]
        raise array_error


def _normalize_test_case(item: Any) -> dict[str, str | None]:
    if not isinstance(item, dict):
        raise ValueError("Each generated test case must be a JSON object.")
    test_type = (optional_string(item, "test_type") or "GENERATED").upper()
    if test_type not in VALID_TEST_TYPES:
        test_type = "GENERATED"
    return {
        "input": optional_string(item, "input") or "",
        "expected_output": optional_string(item, "expected_output"),
        "test_type": test_type,
    }


def _normalize_multiple_answer_tests(problem_text: str, tests: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    if not _is_frequency_sort_problem(problem_text):
        return tests

    normalized: list[dict[str, str | None]] = []
    nulled_count = 0
    removed_count = 0
    for test in tests:
        input_data = test["input"] or ""
        if not input_data.strip():
            removed_count += 1
            continue
        if test.get("expected_output") is not None and _has_frequency_ties(input_data.strip()):
            test = {**test, "expected_output": None}
            nulled_count += 1
        normalized.append(test)

    if not any(test.get("expected_output") for test in normalized):
        normalized.extend(
            [
                {"input": "aaaaabbc", "expected_output": "aaaaabbc", "test_type": "GENERATED"},
                {"input": "zzzzzyxx", "expected_output": "zzzzzxxy", "test_type": "GENERATED"},
                {"input": "1111223", "expected_output": "1111223", "test_type": "GENERATED"},
            ]
        )

    if nulled_count or removed_count:
        logger.warning(
            "Adjusted frequency-sort tests for multiple valid outputs nulled=%s removed=%s final_count=%s",
            nulled_count,
            removed_count,
            len(normalized),
        )
    return normalized[:8]


def _is_frequency_sort_problem(problem_text: str) -> bool:
    lower = problem_text.lower()
    return (
        "frequency of the characters" in lower
        and "decreasing order" in lower
        and ("multiple answers" in lower or "any of them" in lower)
    )


def _has_frequency_ties(value: str) -> bool:
    counts = Counter(value)
    frequency_counts = Counter(counts.values())
    return any(group_size > 1 for group_size in frequency_counts.values())
