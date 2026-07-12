import json
import pytest

from app.model_runtime.base import BaseModelRuntime
from app.solver.code_generator import _normalize_generated_text, _solutions_are_too_similar, generate_solution_variants


class FakeRuntime(BaseModelRuntime):
    def __init__(self, invalid_improved: bool = False) -> None:
        self.invalid_improved = invalid_improved
        self.prompts: list[str] = []

    def load(self) -> None:
        return None

    def status(self) -> dict[str, object]:
        return {"loaded": True}

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        self.prompts.append(prompt)
        if "exactly one BRUTE_FORCE" in prompt:
            approach = "BRUTE_FORCE"
            code = "print('brute')"
            complexity = "O(n^2)"
        elif "exactly one IMPROVED" in prompt:
            if self.invalid_improved:
                return "not-json"
            approach = "IMPROVED"
            code = "print('improved')"
            complexity = "O(n log n)"
        else:
            approach = "OPTIMAL"
            code = "print('optimal')"
            complexity = "O(n)"
        return json.dumps(
            {
                "approach_type": approach,
                "algorithm_pattern": "test",
                "explanation": f"{approach} explanation",
                "pseudocode": approach,
                "code": code,
                "time_complexity": complexity,
                "space_complexity": "O(1)",
            }
        )


class DuplicateThenDistinctRuntime(FakeRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.improved_calls = 0

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        if "exactly one IMPROVED" in prompt:
            self.improved_calls += 1
            if self.improved_calls == 1:
                self.prompts.append(prompt)
                return json.dumps(
                    {
                        "approach_type": "IMPROVED",
                        "algorithm_pattern": "test",
                        "explanation": "Different wording for the same idea.",
                        "pseudocode": "BRUTE_FORCE",
                        "code": "print('brute')",
                        "time_complexity": "O(n log n)",
                        "space_complexity": "O(1)",
                    }
                )
        return super().generate(prompt, max_new_tokens, json_mode=json_mode)


def test_generates_each_approach_as_an_independent_request() -> None:
    runtime = FakeRuntime()

    variants = generate_solution_variants(runtime, "python", "problem text", "test", "evidence")

    assert [item["approach_type"] for item in variants] == ["BRUTE_FORCE", "IMPROVED", "OPTIMAL"]
    assert len(runtime.prompts) == 3


def test_invalid_optional_improved_approach_still_returns_required_pair() -> None:
    runtime = FakeRuntime(invalid_improved=True)

    variants = generate_solution_variants(runtime, "python", "problem text", "test", "evidence")

    assert [item["approach_type"] for item in variants] == ["BRUTE_FORCE", "OPTIMAL"]


def test_duplicate_variant_is_retried_with_distinctness_instruction() -> None:
    runtime = DuplicateThenDistinctRuntime()

    variants = generate_solution_variants(runtime, "python", "problem text", "test", "evidence")

    assert [item["approach_type"] for item in variants] == ["BRUTE_FORCE", "IMPROVED", "OPTIMAL"]
    assert runtime.improved_calls == 2
    assert "previous candidate was invalid, truncated, or duplicated" in runtime.prompts[2]


def test_same_intuition_is_allowed_for_different_implementations() -> None:
    left = {
        "algorithm_pattern": "nested_scan",
        "explanation": "Track whether each value has appeared.",
        "pseudocode": "For every pair, compare their values.",
        "code": "for i in range(n):\n for j in range(i): check(i, j)",
        "time_complexity": "O(n^2)",
        "space_complexity": "O(1)",
    }
    right = {
        "algorithm_pattern": "hash_set",
        "explanation": "Track whether each value has appeared.",
        "pseudocode": "Insert each value into a set and reject repeats.",
        "code": "seen = set()\nfor value in values: seen.add(value)",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
    }

    assert not _solutions_are_too_similar(left, right)


def test_same_code_is_duplicate_even_when_explanation_and_complexity_claims_differ() -> None:
    left = {
        "algorithm_pattern": "scan",
        "explanation": "First explanation.",
        "pseudocode": "Scan values.",
        "code": "for value in values:\n    print(value)",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
    }
    right = {
        **left,
        "explanation": "Unrelated prose.",
        "time_complexity": "O(1)",
    }

    assert _solutions_are_too_similar(left, right)


def test_normalize_generated_text_collapses_whitespace() -> None:
    value = _normalize_generated_text(
        "O(n)   because\n each element is visited once.",
        field_name="time_complexity",
        max_length=1_000,
    )
    assert value == "O(n) because each element is visited once."


def test_normalize_generated_text_bounds_excessive_content() -> None:
    value = _normalize_generated_text("x" * 2_000, field_name="time_complexity", max_length=1_000)
    assert len(value) == 1_000


def test_normalize_generated_text_rejects_blank_content() -> None:
    with pytest.raises(ValueError):
        _normalize_generated_text("   ", field_name="algorithm_pattern", max_length=300)
