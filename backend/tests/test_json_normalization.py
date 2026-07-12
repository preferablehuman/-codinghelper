import json

import pytest

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

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        return json.dumps([EXPLANATION])


class TruncatedThenValidRuntime(BaseModelRuntime):
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, bool]] = []

    def load(self) -> None:
        return None

    def status(self) -> dict[str, object]:
        return {"loaded": True}

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        self.calls.append((prompt, max_new_tokens, json_mode))
        if len(self.calls) == 1:
            return '{"intuition": "cut off"'
        return json.dumps(EXPLANATION)


def test_parse_json_object_unwraps_single_object_array() -> None:
    assert parse_json_object(json.dumps([{"value": "ok"}])) == {"value": "ok"}


def test_parse_json_object_unwraps_named_wrapper() -> None:
    payload = {"result": [EXPLANATION]}
    assert parse_json_object(json.dumps(payload), wrapper_keys=("result",)) == EXPLANATION


def test_incomplete_root_object_is_not_mistaken_for_a_nested_array() -> None:
    with pytest.raises(ValueError, match="incomplete or invalid JSON"):
        parse_json_object('{"code": "cut off", "board": [[1, 2]]')


def test_object_parser_ignores_unrelated_arrays_in_prose() -> None:
    with pytest.raises(ValueError, match="did not contain valid JSON"):
        parse_json_object('* Candidate patterns: ["hash_map", "arrays"]')


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


def test_explanation_retries_a_truncated_response_with_larger_budget() -> None:
    runtime = TruncatedThenValidRuntime()

    result = build_explanation(
        runtime,
        "Validate Sudoku",
        "hash sets",
        {"code": "code", "explanation": "solution"},
        "evidence",
        {"status": "PASSED"},
    )

    assert result == EXPLANATION
    assert len(runtime.calls) == 2
    assert all(call[1] == 12288 for call in runtime.calls)
    assert all(call[2] is True for call in runtime.calls)
    assert "previous response was truncated or malformed" in runtime.calls[1][0]
