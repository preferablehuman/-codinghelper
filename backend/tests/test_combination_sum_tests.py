from app.solver.test_generator import _combination_sum_oracle, _normalize_combination_sum_tests


PROBLEM = "Combination Sum: candidates are distinct and the same number may be chosen an unlimited number of times."


def test_combination_sum_oracle_produces_complete_valid_combinations() -> None:
    assert _combination_sum_oracle([2, 5], 10) == [[2, 2, 2, 2, 2], [5, 5]]


def test_combination_sum_normalizer_replaces_impossible_llm_expectation() -> None:
    tests = [
        {
            "input": "2,5\n10",
            "expected_output": "[[2, 2, 2, 2, 2], [2, 2, 3, 3], [5, 5]]",
            "test_type": "GENERATED",
        }
    ]
    normalized = _normalize_combination_sum_tests(PROBLEM, tests)
    assert normalized[0]["expected_output"] == "[[2, 2, 2, 2, 2], [5, 5]]"


def test_combination_sum_normalizer_supports_solution_one_line_contract() -> None:
    tests = [{"input": "candidates=[2,5], target=10", "expected_output": "[]", "test_type": "GENERATED"}]
    code = "int[] candidates = new int[parts.length - 1]; int target = Integer.parseInt(parts[parts.length - 1]);"
    normalized = _normalize_combination_sum_tests(PROBLEM, tests, code)
    assert normalized[0]["input"] == "2,5,10"
    assert normalized[0]["expected_output"] == "[[2, 2, 2, 2, 2], [5, 5]]"


def test_combination_sum_normalizer_rejects_malformed_inputs() -> None:
    tests = [{"input": "candidates unavailable", "expected_output": "[]", "test_type": "GENERATED"}]
    try:
        _normalize_combination_sum_tests(PROBLEM, tests)
    except ValueError as exc:
        assert "No structurally valid" in str(exc)
    else:
        raise AssertionError("Malformed generated tests must not become assertions")
