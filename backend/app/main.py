import logging
import time

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes_execute import router as execute_router
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_patterns import job_router as job_patterns_router, router as patterns_router
from app.api.routes_result_parts import router as result_parts_router
from app.config import get_settings
from app.db.models import Job
from app.db.session import SessionLocal
from app.logging_config import configure_logging
from app.model_runtime.provider import get_model_runtime
from app.orchestrator.job_manager import set_job_status
from app.orchestrator.statuses import JobStatus


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="CodingHelper Programming Explainer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(patterns_router)
app.include_router(job_patterns_router)
app.include_router(result_parts_router)
app.include_router(execute_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    logger.debug("HTTP request started method=%s path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("HTTP request failed method=%s path=%s elapsed_ms=%s", request.method, request.url.path, elapsed_ms)
        raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "HTTP request completed method=%s path=%s status=%s elapsed_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
def log_startup() -> None:
    settings = get_settings()
    logger.info(
        "Backend service startup started env=%s model_gateway_url=%s",
        settings.app_env,
        settings.model_gateway_url,
    )
    recover_interrupted_jobs()
    initialize_model_runtime()
    logger.info("Backend service startup complete")


def initialize_model_runtime() -> None:
    settings = get_settings()
    started = time.perf_counter()
    logger.info("Startup model gateway check started base_url=%s", settings.model_gateway_url)
    try:
        runtime = get_model_runtime()
        runtime.load()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("Startup model gateway check completed elapsed_ms=%s status=%s", elapsed_ms, runtime.status())
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "Model gateway is unavailable or degraded elapsed_ms=%s error=%s; backend remains available",
            elapsed_ms,
            exc,
        )


def recover_interrupted_jobs() -> None:
    terminal_statuses = [JobStatus.COMPLETED.value, JobStatus.FAILED.value]
    with SessionLocal() as db:
        jobs = list(db.scalars(select(Job).where(~Job.status.in_(terminal_statuses))).all())
        if not jobs:
            logger.info("No interrupted jobs found during startup recovery")
            return
        logger.warning("Marking interrupted jobs as failed count=%s", len(jobs))
        for job in jobs:
            set_job_status(
                db,
                job,
                JobStatus.FAILED,
                error_message="Interrupted by backend restart; rerun the job to start a new pipeline task.",
            )
