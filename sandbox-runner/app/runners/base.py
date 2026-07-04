import logging
import subprocess
import time
from pathlib import Path

from app.security.limits import prepare_process


logger = logging.getLogger(__name__)


def normalize_output(value: str | None) -> str:
    return (value or "").replace("\r\n", "\n").strip()


def run_process(
    command: list[str],
    cwd: Path,
    stdin: str,
    timeout_seconds: int,
    memory_mb: int,
    *,
    limit_memory: bool = True,
) -> dict[str, object]:
    started = time.perf_counter()
    logger.debug(
        "Starting sandbox process command=%s cwd=%s stdin_chars=%s timeout_seconds=%s memory_mb=%s limit_memory=%s",
        command[0],
        cwd,
        len(stdin),
        timeout_seconds,
        memory_mb,
        limit_memory,
    )
    try:
        completed = subprocess.run(
            command,
            input=stdin,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            preexec_fn=lambda: prepare_process(memory_mb if limit_memory else None),
            check=False,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.debug(
            "Sandbox process exited command=%s returncode=%s elapsed_ms=%s stdout_chars=%s stderr_chars=%s",
            command[0],
            completed.returncode,
            elapsed_ms,
            len(completed.stdout or ""),
            len(completed.stderr or ""),
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "execution_time_ms": elapsed_ms,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("Sandbox process timed out command=%s elapsed_ms=%s timeout_seconds=%s", command[0], elapsed_ms, timeout_seconds)
        return {
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Timed out",
            "execution_time_ms": elapsed_ms,
            "timed_out": True,
        }


def summarize_results(results: list[dict[str, object]]) -> dict[str, object]:
    if any(result["status"] == "TIMEOUT" for result in results):
        status = "TIMEOUT"
    elif any(result["status"] == "COMPILE_ERROR" for result in results):
        status = "COMPILE_ERROR"
    elif any(result["status"] == "RUNTIME_ERROR" for result in results):
        status = "RUNTIME_ERROR"
    elif any(result["status"] == "FAILED" for result in results):
        status = "FAILED"
    else:
        status = "PASSED"
    passed = sum(1 for result in results if result["status"] == "PASSED")
    failed = len(results) - passed
    logger.info("Sandbox result summary status=%s passed=%s failed=%s total=%s", status, passed, failed, len(results))
    return {"status": status, "passed_count": passed, "failed_count": failed, "results": results}
