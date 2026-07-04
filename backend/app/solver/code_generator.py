import logging
import re

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_object, require_string, response_preview
from app.model_runtime.prompts import repair_prompt, solution_prompt


logger = logging.getLogger(__name__)


def generate_solution(
    runtime: BaseModelRuntime,
    language: str,
    problem_text: str,
    pattern: str,
    evidence: str,
) -> dict[str, str]:
    logger.info("Generating solution language=%s pattern=%s problem_chars=%s evidence_chars=%s", language, pattern, len(problem_text), len(evidence))
    raw = runtime.generate(solution_prompt(problem_text, language, pattern, evidence), max_new_tokens=4096, json_mode=True)
    try:
        data = parse_json_object(raw)
    except ValueError:
        logger.error("Solution JSON parse failed response_preview=%s", response_preview(raw))
        raise
    try:
        result = _normalize_solution_payload(data, pattern, language=language)
    except ValueError as exc:
        logger.error("Solution payload normalization failed error=%s response_preview=%s", exc, response_preview(raw))
        raise
    logger.info("Solution payload parsed code_chars=%s explanation_chars=%s", len(result["code"]), len(result["explanation"]))
    return result


def repair_solution(
    runtime: BaseModelRuntime,
    language: str,
    problem_text: str,
    evidence: str,
    solution: dict[str, str],
    tests: list[dict[str, str | None]],
    verification: dict[str, object],
) -> dict[str, str]:
    logger.info(
        "Repairing solution language=%s previous_code_chars=%s test_count=%s verification_status=%s",
        language,
        len(solution.get("code", "")),
        len(tests),
        verification.get("status"),
    )
    raw = runtime.generate(
        repair_prompt(problem_text, language, evidence, solution, tests, verification),
        max_new_tokens=4096,
        json_mode=True,
    )
    try:
        data = parse_json_object(raw)
    except ValueError:
        logger.error("Repair JSON parse failed response_preview=%s", response_preview(raw))
        raise
    try:
        result = _normalize_solution_payload(data, solution["algorithm_pattern"], previous_solution=solution, language=language)
    except ValueError as exc:
        logger.error("Repair payload normalization failed error=%s response_preview=%s", exc, response_preview(raw))
        raise
    logger.info("Repaired solution payload parsed code_chars=%s", len(result["code"]))
    return result


def _normalize_solution_payload(
    data: dict[str, object],
    fallback_pattern: str,
    previous_solution: dict[str, str] | None = None,
    language: str = "",
) -> dict[str, str]:
    code = _sanitize_code(require_string(data, "code"), language)
    defaults_used: list[str] = []

    def field(key: str, default: str) -> str:
        value = optional_string(data, key)
        if value:
            return value
        defaults_used.append(key)
        return default

    result = {
        "approach_type": field("approach_type", "FINAL"),
        "algorithm_pattern": field("algorithm_pattern", fallback_pattern),
        "explanation": field(
            "explanation",
            (previous_solution or {}).get("explanation", "Generated solution for the programming problem."),
        ),
        "pseudocode": field("pseudocode", _fallback_pseudocode(fallback_pattern)),
        "code": code,
        "time_complexity": field("time_complexity", (previous_solution or {}).get("time_complexity", "Not specified.")),
        "space_complexity": field("space_complexity", (previous_solution or {}).get("space_complexity", "Not specified.")),
    }
    if defaults_used:
        logger.warning("Solution payload missing optional fields; defaults used fields=%s", defaults_used)
    return result


def _fallback_pseudocode(pattern: str) -> str:
    return "\n".join(
        [
            "1. Read and parse the input.",
            f"2. Apply the {pattern} strategy to maintain the required state.",
            "3. Compute the requested result from that state.",
            "4. Print the result in the required output format.",
        ]
    )


def _sanitize_code(code: str, language: str) -> str:
    if language.lower() != "java":
        return code
    return _ensure_java_standard_imports(code)


def _ensure_java_standard_imports(code: str) -> str:
    stripped = code.lstrip()
    if not stripped or "class " not in stripped:
        return code
    if "import java.util.*;" in code and "import java.io.*;" in code:
        return code

    lines = code.splitlines()
    insert_at = 0
    package_match = False
    for index, line in enumerate(lines):
        if re.match(r"\s*package\s+[\w.]+\s*;", line):
            insert_at = index + 1
            package_match = True
            break
        if line.strip():
            break
    if package_match:
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1

    imports: list[str] = []
    if "import java.util.*;" not in code:
        imports.append("import java.util.*;")
    if "import java.io.*;" not in code:
        imports.append("import java.io.*;")
    if not imports:
        return code

    logger.info("Added Java standard wildcard imports imports=%s", imports)
    return "\n".join([*lines[:insert_at], *imports, *lines[insert_at:]])
