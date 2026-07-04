import logging
import tempfile
import os
from pathlib import Path

from app.runners.base import normalize_output, run_process, summarize_results


logger = logging.getLogger(__name__)


def run_python(code: str, tests: list[dict[str, str | None]], timeout_seconds: int, memory_mb: int) -> dict[str, object]:
    if not tests:
        tests = [{"input": "", "expected_output": None}]
    results: list[dict[str, object]] = []
    work_dir = os.getenv("SANDBOX_WORK_DIR")
    if work_dir:
        Path(work_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Python runner starting code_chars=%s test_count=%s work_dir=%s", len(code), len(tests), work_dir or "tmp")
    with tempfile.TemporaryDirectory(prefix="study-buddy-python-", dir=work_dir) as temp_name:
        temp_dir = Path(temp_name)
        script = temp_dir / "solution.py"
        script.write_text(code, encoding="utf-8")
        for index, test in enumerate(tests):
            process = run_process(["python", str(script)], temp_dir, test.get("input") or "", timeout_seconds, memory_mb)
            stdout = normalize_output(str(process["stdout"]))
            expected = test.get("expected_output")
            if process["timed_out"]:
                status = "TIMEOUT"
            elif process["returncode"] != 0:
                status = "RUNTIME_ERROR"
            elif expected is not None and stdout != normalize_output(expected):
                status = "FAILED"
            else:
                status = "PASSED"
            logger.debug(
                "Python test completed index=%s status=%s stdout_chars=%s stderr_chars=%s",
                index,
                status,
                len(str(process["stdout"])),
                len(str(process["stderr"])),
            )
            results.append(
                {
                    "test_index": index,
                    "status": status,
                    "stdout": str(process["stdout"]),
                    "stderr": str(process["stderr"]),
                    "execution_time_ms": process["execution_time_ms"],
                }
            )
    logger.info("Python runner finished test_count=%s", len(results))
    return summarize_results(results)
