from sqlalchemy import Text

from app.db.models import GeneratedSolution, ReusableSolution


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
