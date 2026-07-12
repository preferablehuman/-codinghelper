import logging
import re
from collections import Counter
from typing import Any

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_array, parse_json_object, response_preview
from app.model_runtime.prompts import tests_prompt as build_tests_prompt

VALID_TEST_TYPES = {"SAMPLE", "EDGE", "GENERATED", "RANDOM"}
logger = logging.getLogger(__name__)


def generate_tests(runtime: BaseModelRuntime, problem_text: str, language: str, solution: dict[str, str]) -> list[dict[str, str | None]]:
    logger.info("Generating tests language=%s problem_chars=%s code_chars=%s", language, len(problem_text), len(solution.get("code", "")))
    raw = runtime.generate(build_tests_prompt(problem_text, language, solution), max_new_tokens=4096, json_mode=True, schema_name="tests")
    try:
        data = _parse_test_payload(raw)
    except ValueError:
        logger.error("Test JSON parse failed response_preview=%s", response_preview(raw))
        raise
    tests = [_normalize_test_case(item) for item in data]
    tests = _normalize_multiple_answer_tests(problem_text, tests)
    tests = _normalize_sudoku_tests(problem_text, tests)
    tests = _normalize_combination_sum_tests(problem_text, tests, solution.get("code", ""))
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
    return normalized


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


def _normalize_sudoku_tests(problem_text: str, tests: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    if "sudoku" not in problem_text.casefold():
        return tests
    seed: tuple[list[str], list[str]] | None = None
    for test in tests:
        puzzle = _parse_sudoku_grid(test.get("input") or "", allow_empty=True)
        solution = _parse_sudoku_grid(test.get("expected_output") or "", allow_empty=False)
        if puzzle and solution and _valid_sudoku_solution(solution) and _clues_match(puzzle, solution):
            seed = puzzle, solution
            break
    if seed is None:
        logger.warning("Could not derive deterministic Sudoku tests because no valid solved sample was generated")
        return tests
    puzzle, solution = seed
    normalized: list[dict[str, str | None]] = [
        {"input": "\n".join(puzzle), "expected_output": "\n".join(solution), "test_type": "SAMPLE"},
        {"input": "\n".join(solution), "expected_output": "\n".join(solution), "test_type": "EDGE"},
    ]
    positions = [(row, (row * 4 + 1) % 9) for row in range(9)]
    for blank_count in range(1, 9):
        derived = [list(row) for row in solution]
        for row, column in positions[:blank_count]:
            derived[row][column] = "."
        normalized.append(
            {
                "input": "\n".join("".join(row) for row in derived),
                "expected_output": "\n".join(solution),
                "test_type": "GENERATED",
            }
        )
    logger.info("Replaced unsafe generated Sudoku cases with deterministic asserting tests test_count=%s", len(normalized))
    return normalized


def _parse_sudoku_grid(value: str, *, allow_empty: bool) -> list[str] | None:
    lines = []
    for raw in value.splitlines():
        line = "".join(character for character in raw if character in "123456789.0").replace("0", ".")
        if len(line) == 9:
            lines.append(line)
    if len(lines) != 9:
        return None
    if not allow_empty and any("." in line for line in lines):
        return None
    return lines


def _valid_sudoku_solution(grid: list[str]) -> bool:
    required = set("123456789")
    if any(set(row) != required for row in grid):
        return False
    if any({grid[row][column] for row in range(9)} != required for column in range(9)):
        return False
    return all(
        {grid[row][column] for row in range(box_row, box_row + 3) for column in range(box_column, box_column + 3)} == required
        for box_row in (0, 3, 6)
        for box_column in (0, 3, 6)
    )


def _clues_match(puzzle: list[str], solution: list[str]) -> bool:
    return all(puzzle[row][column] in {".", solution[row][column]} for row in range(9) for column in range(9))


def _normalize_combination_sum_tests(
    problem_text: str, tests: list[dict[str, str | None]], solution_code: str = ""
) -> list[dict[str, str | None]]:
    lower = problem_text.casefold()
    if "combination sum" not in lower or "unlimited number of times" not in lower:
        return tests

    normalized: list[dict[str, str | None]] = []
    rejected = 0
    for test in tests:
        parsed = _parse_combination_sum_input(test.get("input") or "")
        if parsed is None:
            rejected += 1
            continue
        candidates, target = parsed
        one_line_contract = "parts.length - 1" in solution_code or "parts.length-1" in solution_code
        normalized_input = ",".join(str(value) for value in [*candidates, target]) if one_line_contract else f"{','.join(str(value) for value in candidates)}\n{target}"
        normalized.append(
            {
                **test,
                "input": normalized_input,
                "expected_output": str(_combination_sum_oracle(candidates, target)),
            }
        )
    if rejected:
        logger.warning("Rejected malformed Combination Sum tests count=%s", rejected)
    if not normalized:
        raise ValueError("No structurally valid Combination Sum tests were generated.")
    logger.info("Recomputed Combination Sum expected outputs with deterministic oracle test_count=%s", len(normalized))
    return normalized


def _parse_combination_sum_input(value: str) -> tuple[list[int], int] | None:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) not in {1, 2}:
        return None
    values = [int(match) for match in re.findall(r"-?\d+", lines[0])]
    if len(lines) == 1:
        if len(values) < 2:
            return None
        candidates, target = values[:-1], values[-1]
    else:
        target_values = re.findall(r"-?\d+", lines[1])
        if len(target_values) != 1:
            return None
        candidates, target = values, int(target_values[0])
    if not candidates or len(set(candidates)) != len(candidates) or any(candidate <= 0 for candidate in candidates) or target < 0:
        return None
    return sorted(candidates), target


def _combination_sum_oracle(candidates: list[int], target: int) -> list[list[int]]:
    results: list[list[int]] = []

    def search(start: int, remaining: int, current: list[int]) -> None:
        if remaining == 0:
            results.append(list(current))
            return
        for index in range(start, len(candidates)):
            candidate = candidates[index]
            if candidate > remaining:
                break
            current.append(candidate)
            search(index, remaining - candidate, current)
            current.pop()

    search(0, target, [])
    return results
