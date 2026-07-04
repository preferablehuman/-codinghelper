import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Job
from app.orchestrator.statuses import STATUS_PROGRESS, JobStatus


logger = logging.getLogger(__name__)


def set_job_status(db: Session, job: Job, status: JobStatus, error_message: str | None = None) -> None:
    progress_percent, current_step = STATUS_PROGRESS[status]
    previous_status = job.status
    job.status = status.value
    job.progress_percent = progress_percent
    job.current_step = current_step
    job.error_message = error_message
    job.updated_at = datetime.now(timezone.utc)
    if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
        job.completed_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()
    db.refresh(job)
    if error_message:
        logger.error(
            "Job status changed job_id=%s from=%s to=%s progress=%s error=%s",
            job.id,
            previous_status,
            status.value,
            progress_percent,
            error_message,
        )
    else:
        logger.info(
            "Job status changed job_id=%s from=%s to=%s progress=%s step=%s",
            job.id,
            previous_status,
            status.value,
            progress_percent,
            current_step,
        )
