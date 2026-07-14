import logging
import os
import time
from typing import Literal

from fastapi import FastAPI
from fastapi import Request
from pydantic import BaseModel, Field

from app.logging_config import configure_logging
from app.runners.java_runner import run_java
from app.runners.python_runner import run_python


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="CodingHelper Sandbox Runner", version="0.1.0")


class RunTest(BaseModel):
    input: str = ""
    expected_output: str | None = None


class RunRequest(BaseModel):
    language: Literal["python", "java"]
    code: str = Field(min_length=1)
    tests: list[RunTest] = Field(default_factory=list)
    timeout_seconds: int = 5
    memory_mb: int = 256


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
    logger.info("Sandbox runner startup complete")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "sandbox-runner",
        "timeout_seconds": int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "5")),
        "memory_mb": int(os.getenv("SANDBOX_MEMORY_MB", "256")),
    }


@app.post("/run")
def run_code(payload: RunRequest) -> dict[str, object]:
    tests = [test.model_dump() for test in payload.tests]
    logger.info(
        "Sandbox run requested language=%s code_chars=%s test_count=%s timeout_seconds=%s memory_mb=%s",
        payload.language,
        len(payload.code),
        len(tests),
        payload.timeout_seconds,
        payload.memory_mb,
    )
    if payload.language == "java":
        result = run_java(payload.code, tests, payload.timeout_seconds, payload.memory_mb)
    else:
        result = run_python(payload.code, tests, payload.timeout_seconds, payload.memory_mb)
    logger.info(
        "Sandbox run completed language=%s status=%s passed=%s failed=%s",
        payload.language,
        result.get("status"),
        result.get("passed_count"),
        result.get("failed_count"),
    )
    return result
