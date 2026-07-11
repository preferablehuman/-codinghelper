import json

from app.explainer.explanation_generator import build_explanation
from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import parse_json_object


EXPLANATION = {
    "intuition": "Track seen values.",
    "brute_force": "Check each region independently.",
    "optimized_approach": "Check all regions in one traversal.",
    "dry_run": "Inspect a representative cell.",
    "pitfalls": "Ignore empty cells.",
    "complexity_analysis": "O(1) for a fixed board.",
}


class ArrayExplanationRuntime(BaseModelRuntime):
    def load(self) -> None:
        return None

    def status(self) -> dict[str, object]:
        return {"loaded": True}

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False) -> str:
        return json.dumps([EXPLANATION])


def test_parse_json_object_unwraps_single_object_array() -> None:
    assert parse_json_object(json.dumps([{"value": "ok"}])) == {"value": "ok"}


def test_parse_json_object_unwraps_named_wrapper() -> None:
    payload = {"result": [EXPLANATION]}
    assert parse_json_object(json.dumps(payload), wrapper_keys=("result",)) == EXPLANATION


def test_explanation_accepts_single_object_array_response() -> None:
    result = build_explanation(
        ArrayExplanationRuntime(),
        "Validate Sudoku",
        "hash sets",
        {"code": "code", "explanation": "solution"},
        "evidence",
        {"status": "PASSED"},
    )
    assert result == EXPLANATION
