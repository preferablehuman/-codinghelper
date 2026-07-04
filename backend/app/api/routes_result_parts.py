import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EvidenceItem, Explanation, GeneratedSolution, Job, SlideArtifact, SourceDocument, VerificationRun
from app.db.session import get_db
from app.schemas import EvidenceItemOut, ExplanationOut, GeneratedSolutionOut, SlideArtifactOut, SourceDocumentOut, VerificationRunOut

router = APIRouter(prefix="/api/jobs", tags=["job result parts"])
logger = logging.getLogger(__name__)


def _ensure_job(db: Session, job_id: str) -> None:
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


@router.get("/{job_id}/sources", response_model=list[SourceDocumentOut])
def get_sources(job_id: str, db: Session = Depends(get_db)) -> list[SourceDocument]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(SourceDocument).where(SourceDocument.job_id == job_id)).all())
    logger.debug("Loaded job sources job_id=%s count=%s", job_id, len(rows))
    return rows


@router.get("/{job_id}/evidence", response_model=list[EvidenceItemOut])
def get_evidence(job_id: str, db: Session = Depends(get_db)) -> list[EvidenceItem]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(EvidenceItem).where(EvidenceItem.job_id == job_id)).all())
    logger.debug("Loaded job evidence job_id=%s count=%s", job_id, len(rows))
    return rows


@router.get("/{job_id}/solution", response_model=list[GeneratedSolutionOut])
def get_solution(job_id: str, db: Session = Depends(get_db)) -> list[GeneratedSolution]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(GeneratedSolution).where(GeneratedSolution.job_id == job_id)).all())
    logger.debug("Loaded job solutions job_id=%s count=%s", job_id, len(rows))
    return rows


@router.get("/{job_id}/verification", response_model=list[VerificationRunOut])
def get_verification(job_id: str, db: Session = Depends(get_db)) -> list[VerificationRun]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(VerificationRun).where(VerificationRun.job_id == job_id)).all())
    logger.debug("Loaded job verification runs job_id=%s count=%s", job_id, len(rows))
    return rows


@router.get("/{job_id}/explanation", response_model=list[ExplanationOut])
def get_explanation(job_id: str, db: Session = Depends(get_db)) -> list[Explanation]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(Explanation).where(Explanation.job_id == job_id)).all())
    logger.debug("Loaded job explanations job_id=%s count=%s", job_id, len(rows))
    return rows


@router.get("/{job_id}/slides", response_model=list[SlideArtifactOut])
def get_slides(job_id: str, db: Session = Depends(get_db)) -> list[SlideArtifact]:
    _ensure_job(db, job_id)
    rows = list(db.scalars(select(SlideArtifact).where(SlideArtifact.job_id == job_id)).all())
    logger.debug("Loaded job slides job_id=%s count=%s", job_id, len(rows))
    return rows
