import json

from app.model_runtime.base import BaseModelRuntime
from app.solver.code_generator import generate_solution_variants


class FakeRuntime(BaseModelRuntime):
    def __init__(self, invalid_improved: bool = False) -> None:
        self.invalid_improved = invalid_improved
        self.prompts: list[str] = []

    def load(self) -> None:
        return None

    def status(self) -> dict[str, object]:
        return {"loaded": True}

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False) -> str:
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


def test_generates_each_approach_as_an_independent_request() -> None:
    runtime = FakeRuntime()

    variants = generate_solution_variants(runtime, "python", "problem text", "test", "evidence")

    assert [item["approach_type"] for item in variants] == ["BRUTE_FORCE", "IMPROVED", "OPTIMAL"]
    assert len(runtime.prompts) == 3


def test_invalid_optional_improved_approach_still_returns_required_pair() -> None:
    runtime = FakeRuntime(invalid_improved=True)

    variants = generate_solution_variants(runtime, "python", "problem text", "test", "evidence")

    assert [item["approach_type"] for item in variants] == ["BRUTE_FORCE", "OPTIMAL"]
