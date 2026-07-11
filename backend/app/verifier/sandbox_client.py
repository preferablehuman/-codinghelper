import logging
import time

import httpx

from app.config import get_settings


logger = logging.getLogger(__name__)


def verify_code(
    language: str,
    code: str,
    tests: list[dict[str, str | None]],
    timeout_seconds: int = 5,
    memory_mb: int = 256,
) -> dict[str, object]:
    settings = get_settings()
    payload = {
        "language": language,
        "code": code,
        "tests": [{"input": test["input"], "expected_output": test.get("expected_output")} for test in tests],
        "timeout_seconds": timeout_seconds,
        "memory_mb": memory_mb,
    }
    try:
        started = time.perf_counter()
        logger.info(
            "Calling sandbox runner url=%s language=%s code_chars=%s test_count=%s",
            settings.sandbox_runner_url,
            language,
            len(code),
            len(tests),
        )
        response = httpx.post(f"{settings.sandbox_runner_url}/run", json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Sandbox verification response status=%s passed=%s failed=%s elapsed_ms=%s",
            result.get("status"),
            result.get("passed_count"),
            result.get("failed_count"),
            elapsed_ms,
        )
        return result
    except Exception as exc:
        logger.exception("Sandbox verification call failed language=%s test_count=%s", language, len(tests))
        return {
            "status": "INTERNAL_ERROR",
            "passed_count": 0,
            "failed_count": len(tests),
            "results": [],
            "stdout": "",
            "stderr": f"Sandbox unavailable: {exc}",
        }
