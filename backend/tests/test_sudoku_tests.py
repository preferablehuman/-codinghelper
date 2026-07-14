from app.solver.test_generator import _normalize_sudoku_tests, _valid_sudoku_solution


SOLUTION = [
    "534678912", "672195348", "198342567", "859761423", "426853791",
    "713924856", "961537284", "287419635", "345286179",
]
PUZZLE = [
    "53..7....", "6..195...", ".98....6.", "8...6...3", "4..8.3..1",
    "7...2...6", ".6....28.", "...419..5", "....8..79",
]


def test_sudoku_postprocessor_replaces_unsafe_model_cases() -> None:
    tests = [
        {"input": "\n".join(PUZZLE), "expected_output": "\n".join(SOLUTION), "test_type": "SAMPLE"},
        {"input": "\n".join(["0" * 9] * 9), "expected_output": "invalid", "test_type": "RANDOM"},
    ]
    normalized = _normalize_sudoku_tests("Solve this 9x9 Sudoku puzzle", tests)
    assert len(normalized) == 10
    assert all("0" not in str(test["input"]) for test in normalized)
    assert all(test["expected_output"] == "\n".join(SOLUTION) for test in normalized)


def test_sudoku_solution_validator_rejects_duplicate_rows() -> None:
    assert _valid_sudoku_solution(SOLUTION)
    assert not _valid_sudoku_solution([SOLUTION[0]] * 9)
