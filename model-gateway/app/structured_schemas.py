import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, RootModel, TypeAdapter
from app.json_contract import StructuredOutputError


class ProblemEquivalence(BaseModel):
    relation: Literal["EXACT", "EQUIVALENT", "RELATED", "DIFFERENT"]
    confidence: float = Field(ge=0, le=1)
    matching_requirements: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    adaptation_required: list[str] = Field(default_factory=list)
    reason: str


class ProblemAnalysis(BaseModel):
    summary: str
    selected_pattern: str
    candidate_patterns: list[str]
    edge_cases: list[str]
    objective: str = ""
    input_entities: list[str] = Field(default_factory=list)
    output_requirement: str = ""
    constraints: list[Any] = Field(default_factory=list)
    semantic_flags: dict[str, Any] = Field(default_factory=dict)


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Solution(StrictPayload):
    approach_type: str
    algorithm_pattern: str
    explanation: str
    pseudocode: str
    code: str
    time_complexity: str
    space_complexity: str


class GeneratedTest(StrictPayload):
    input: str
    expected_output: str | None
    test_type: Literal["SAMPLE", "EDGE", "GENERATED", "RANDOM"]


class GeneratedTests(RootModel[list[GeneratedTest]]):
    pass


class Explanation(StrictPayload):
    intuition: str
    brute_force: str
    optimized_approach: str
    dry_run: Any
    pitfalls: Any
    complexity_analysis: Any


class PatternLesson(StrictPayload):
    display_name: str
    overview: str
    mental_model: str
    recognition_cues: str
    core_operations: str
    invariants: str
    worked_example: str
    implementation_guide: str
    complexity_tradeoffs: str
    pitfalls: str
    related_patterns: str
    evidence_summary: str


SCHEMAS = {
    "problem_analysis": TypeAdapter(ProblemAnalysis),
    "problem_equivalence": TypeAdapter(ProblemEquivalence),
    "solution": TypeAdapter(Solution),
    "tests": TypeAdapter(GeneratedTests),
    "explanation": TypeAdapter(Explanation),
    "pattern_lesson": TypeAdapter(PatternLesson),
}


def validate_schema(text: str, schema_name: str | None) -> str:
    if not schema_name:
        return text
    value = json.loads(text)
    try:
        validated = SCHEMAS[schema_name].validate_python(value)
    except Exception as exc:
        raise StructuredOutputError(f"Structured output failed approved schema {schema_name}.") from exc
    if isinstance(validated, BaseModel):
        value = validated.model_dump()
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def schema_for(schema_name: str | None) -> dict[str, Any] | None:
    return SCHEMAS[schema_name].json_schema() if schema_name else None


def schema_model_for(schema_name: str | None) -> type[BaseModel] | None:
    models: dict[str, type[BaseModel]] = {
        "problem_analysis": ProblemAnalysis,
        "problem_equivalence": ProblemEquivalence,
        "solution": Solution,
        "tests": GeneratedTests,
        "explanation": Explanation,
        "pattern_lesson": PatternLesson,
    }
    return models.get(schema_name or "")
