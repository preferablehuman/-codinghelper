from types import SimpleNamespace
from unittest.mock import patch

from app.orchestrator.pipeline import run_job_pipeline
from app.orchestrator.statuses import JobStatus


class FakeScalars:
    def __init__(self, session, job):
        self.session = session
        self.job = job

    def first(self):
        assert self.session.rolled_back, "job recovery queried before transaction rollback"
        return self.job


class FakeSession:
    def __init__(self):
        self.job = SimpleNamespace(id="job-id", language="java", status=JobStatus.PENDING.value, completed_at=None)
        self.rolled_back = False

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def get(self, model, job_id): return self.job
    def rollback(self): self.rolled_back = True
    def scalars(self, statement): return FakeScalars(self, self.job)


def test_pipeline_rolls_back_before_marking_job_failed() -> None:
    session = FakeSession()
    with patch("app.orchestrator.pipeline.SessionLocal", return_value=session), patch(
        "app.orchestrator.pipeline.normalize_problem", side_effect=RuntimeError("persistence failed")
    ), patch("app.orchestrator.pipeline.set_job_status") as set_status:
        run_job_pipeline("job-id")

    assert session.rolled_back
    assert set_status.call_args.args[2] == JobStatus.FAILED
