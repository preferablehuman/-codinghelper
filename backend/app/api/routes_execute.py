import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas import CodeExecutionRequest, CodeExecutionResponse
from app.verifier.sandbox_client import verify_code


router = APIRouter(prefix="/api/execute", tags=["execute"])
logger = logging.getLogger(__name__)
SUPPORTED_LANGUAGES = {"java", "python"}


@router.post("", response_model=CodeExecutionResponse)
def execute_code(payload: CodeExecutionRequest) -> dict[str, object]:
    language = payload.language.lower()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Execution is only available for: {', '.join(sorted(SUPPORTED_LANGUAGES))}",
        )

    if payload.tests:
        tests = [
            {"input": test.input, "expected_output": test.expected_output if test.expected_output and test.expected_output.strip() else None}
            for test in payload.tests
        ]
    else:
        expected_output = payload.expected_output
        if expected_output is not None and not expected_output.strip():
            expected_output = None
        tests = [{"input": payload.input, "expected_output": expected_output}]

    logger.info(
        "Interactive code execution requested language=%s code_chars=%s test_count=%s input_chars=%s",
        language,
        len(payload.code),
        len(tests),
        sum(len(test["input"]) for test in tests),
    )
    result = verify_code(
        language,
        payload.code,
        tests,
        timeout_seconds=payload.timeout_seconds,
        memory_mb=payload.memory_mb,
    )
    execution_times = [
        int(item.get("execution_time_ms", 0))
        for item in result.get("results", [])
        if isinstance(item, dict) and item.get("execution_time_ms") is not None
    ]
    result["average_execution_time_ms"] = round(sum(execution_times) / len(execution_times), 2) if execution_times else None
    return result
