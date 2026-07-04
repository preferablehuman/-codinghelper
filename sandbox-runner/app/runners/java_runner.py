import logging
import tempfile
import os
import re
from pathlib import Path

from app.runners.base import normalize_output, run_process, summarize_results


logger = logging.getLogger(__name__)


def run_java(code: str, tests: list[dict[str, str | None]], timeout_seconds: int, memory_mb: int) -> dict[str, object]:
    if not tests:
        tests = [{"input": "", "expected_output": None}]
    results: list[dict[str, object]] = []
    java_memory_mb = max(memory_mb, 1024)
    java_heap_mb = min(max(memory_mb // 2, 96), 128)
    work_dir = os.getenv("SANDBOX_WORK_DIR")
    if work_dir:
        Path(work_dir).mkdir(parents=True, exist_ok=True)
    class_name = _entrypoint_class_name(code)
    logger.info(
        "Java runner starting code_chars=%s test_count=%s work_dir=%s class_name=%s memory_mb=%s heap_mb=%s",
        len(code),
        len(tests),
        work_dir or "tmp",
        class_name,
        java_memory_mb,
        java_heap_mb,
    )
    with tempfile.TemporaryDirectory(prefix="study-buddy-java-", dir=work_dir) as temp_name:
        temp_dir = Path(temp_name)
        source = temp_dir / f"{class_name}.java"
        source.write_text(code, encoding="utf-8")
        javac_memory_flags = [
            f"-J-Xmx{java_heap_mb}m",
            "-J-XX:MaxMetaspaceSize=64m",
            "-J-XX:CompressedClassSpaceSize=16m",
            "-J-XX:ReservedCodeCacheSize=16m",
        ]
        java_memory_flags = [
            f"-Xmx{java_heap_mb}m",
            "-XX:MaxMetaspaceSize=64m",
            "-XX:CompressedClassSpaceSize=16m",
            "-XX:ReservedCodeCacheSize=16m",
            "-Xss512k",
        ]
        compile_result = run_process(
            ["javac", *javac_memory_flags, source.name],
            temp_dir,
            "",
            timeout_seconds,
            java_memory_mb,
            limit_memory=False,
        )
        if compile_result["returncode"] != 0 or compile_result["timed_out"]:
            logger.warning(
                "Java compilation failed status=%s returncode=%s stdout_chars=%s stderr_chars=%s stdout_preview=%s stderr_preview=%s",
                "TIMEOUT" if compile_result["timed_out"] else "COMPILE_ERROR",
                compile_result["returncode"],
                len(str(compile_result["stdout"])),
                len(str(compile_result["stderr"])),
                _preview(str(compile_result["stdout"])),
                _preview(str(compile_result["stderr"])),
            )
            return summarize_results(
                [
                    {
                        "test_index": 0,
                        "status": "COMPILE_ERROR" if not compile_result["timed_out"] else "TIMEOUT",
                        "stdout": str(compile_result["stdout"]),
                        "stderr": str(compile_result["stderr"]),
                        "execution_time_ms": compile_result["execution_time_ms"],
                    }
                ]
            )
        for index, test in enumerate(tests):
            process = run_process(
                ["java", *java_memory_flags, class_name],
                temp_dir,
                test.get("input") or "",
                timeout_seconds,
                java_memory_mb,
                limit_memory=False,
            )
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
                "Java test completed index=%s status=%s stdout_chars=%s stderr_chars=%s",
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
    logger.info("Java runner finished test_count=%s", len(results))
    return summarize_results(results)


def _entrypoint_class_name(code: str) -> str:
    public_match = re.search(r"\bpublic\s+class\s+([A-Za-z_$][A-Za-z0-9_$]*)", code)
    if public_match:
        return public_match.group(1)
    class_match = re.search(r"\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)", code)
    if class_match:
        return class_match.group(1)
    return "Main"


def _preview(value: str, limit: int = 600) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
