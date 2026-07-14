import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Job
from app.db.session import get_db
from app.orchestrator.pipeline import run_job_pipeline
from app.orchestrator.statuses import JobStatus
from app.schemas import JobCreate, JobCreated, JobDetail, JobListItem, JobStatusResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


def _get_job_or_404(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> JobCreated:
    logger.info(
        "Creating job language=%s source_url_count=%s problem_chars=%s",
        payload.language,
        len(payload.source_urls),
        len(payload.problem_text),
    )
    job = Job(
        title=payload.title,
        problem_text=payload.problem_text,
        language=payload.language.lower(),
        difficulty=None,
        source_urls_json=json.dumps(payload.source_urls),
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_job_pipeline, job.id)
    logger.info("Created job job_id=%s status=%s", job.id, job.status)
    return JobCreated(job_id=job.id, status=job.status)


@router.get("", response_model=list[JobListItem])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    jobs = list(db.scalars(select(Job).order_by(desc(Job.created_at))).all())
    logger.debug("Listed jobs count=%s", len(jobs))
    return jobs


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    stmt = (
        select(Job)
        .options(
            selectinload(Job.sources),
            selectinload(Job.evidence_items),
            selectinload(Job.solutions),
            selectinload(Job.test_cases),
            selectinload(Job.verification_runs),
            selectinload(Job.explanations),
            selectinload(Job.slide_artifacts),
        )
        .where(Job.id == job_id)
    )
    job = db.scalars(stmt).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    logger.debug("Loaded job detail job_id=%s status=%s", job.id, job.status)
    return job


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = _get_job_or_404(db, job_id)
    logger.debug("Loaded job status job_id=%s status=%s progress=%s", job.id, job.status, job.progress_percent)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        error_message=job.error_message,
    )


@router.post("/{job_id}/rerun", response_model=JobCreated)
def rerun_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> JobCreated:
    job = _get_job_or_404(db, job_id)
    logger.info("Rerunning job job_id=%s previous_status=%s", job.id, job.status)
    job.verification_runs.clear()
    job.explanations.clear()
    job.slide_artifacts.clear()
    job.test_cases.clear()
    job.evidence_items.clear()
    job.solutions.clear()
    job.sources.clear()
    db.flush()
    job.status = JobStatus.PENDING.value
    job.progress_percent = 5
    job.current_step = "Queued for rerun"
    job.error_message = None
    job.pattern_lesson_id = None
    job.completed_at = None
    db.commit()
    background_tasks.add_task(run_job_pipeline, job.id)
    logger.info("Queued job rerun job_id=%s", job.id)
    return JobCreated(job_id=job.id, status=job.status)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> None:
    job = _get_job_or_404(db, job_id)
    logger.info("Deleting job job_id=%s status=%s", job.id, job.status)
    db.delete(job)
    db.commit()
