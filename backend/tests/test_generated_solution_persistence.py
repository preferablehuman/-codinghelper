import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.models import GeneratedSolution, Job


def test_generated_solution_accepts_long_complexity_descriptions() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL persistence validation")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection) as session:
                job = Job(problem_text="Persistence regression problem", language="java")
                session.add(job)
                session.flush()
                solution = GeneratedSolution(
                    job_id=job.id,
                    approach_type="IMPROVED",
                    algorithm_pattern="Backtracking with bitmasking, constraint propagation, and minimum remaining values ordering " * 2,
                    explanation="Explanation",
                    pseudocode="Pseudocode",
                    code="public class Main {}",
                    time_complexity="O(9^m), where m is the number of empty cells, with significant pruning from bitmask-based constraints and minimum-remaining-values ordering. " * 2,
                    space_complexity="O(m), accounting for the recursion stack and the list of unresolved cells maintained during search. " * 2,
                )
                session.add(solution)
                session.flush()
                assert len(solution.algorithm_pattern) > 120
                assert len(solution.time_complexity) > 120
                assert len(solution.space_complexity) > 120
                stored = connection.execute(
                    text("SELECT length(algorithm_pattern), length(time_complexity), length(space_complexity) FROM generated_solutions WHERE id=:id"),
                    {"id": solution.id},
                ).one()
                assert all(length > 120 for length in stored)
        finally:
            transaction.rollback()
