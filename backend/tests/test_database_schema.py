from sqlalchemy import String, Text

from app.db.models import GeneratedSolution, Job, PatternLesson, ReusableSolution


def test_generated_solution_descriptive_columns_are_text() -> None:
    table = GeneratedSolution.__table__
    assert isinstance(table.c.algorithm_pattern.type, Text)
    assert isinstance(table.c.time_complexity.type, Text)
    assert isinstance(table.c.space_complexity.type, Text)


def test_reusable_solution_descriptive_columns_are_text() -> None:
    table = ReusableSolution.__table__
    assert isinstance(table.c.algorithm_pattern.type, Text)
    assert isinstance(table.c.time_complexity.type, Text)
    assert isinstance(table.c.space_complexity.type, Text)


def test_pattern_lesson_has_a_unique_reusable_key_and_deep_text_fields() -> None:
    table = PatternLesson.__table__
    assert isinstance(table.c.pattern_key.type, String)
    assert any(constraint.name == "uq_pattern_lessons_pattern_key" for constraint in table.constraints)
    for field in (
        "overview",
        "mental_model",
        "recognition_cues",
        "core_operations",
        "invariants",
        "worked_example",
        "implementation_guide",
        "complexity_tradeoffs",
        "pitfalls",
        "related_patterns",
        "evidence_summary",
    ):
        assert isinstance(table.c[field].type, Text)


def test_job_can_link_to_a_reusable_pattern_lesson() -> None:
    foreign_keys = list(Job.__table__.c.pattern_lesson_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "pattern_lessons.id"
