import logging
import re
from difflib import SequenceMatcher

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_object, require_string, response_preview
from app.model_runtime.prompts import repair_prompt, solution_prompt, solution_variant_prompt


logger = logging.getLogger(__name__)
APPROACH_ORDER = {"BRUTE_FORCE": 0, "IMPROVED": 1, "AVERAGE": 1, "OPTIMAL": 2, "EXPECTED": 2, "FINAL": 2}
MAX_ALGORITHM_PATTERN_LENGTH = 300
MAX_COMPLEXITY_DESCRIPTION_LENGTH = 1_000


def _normalize_generated_text(value: str, *, field_name: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"Generated field {field_name!r} cannot be blank.")
    if len(normalized) > max_length:
        logger.warning(
            "Generated field exceeded expected length field=%s chars=%s max_chars=%s",
            field_name,
            len(normalized),
            max_length,
        )
        normalized = normalized[:max_length].rstrip()
    return normalized


def generate_solution(
    runtime: BaseModelRuntime,
    language: str,
    problem_text: str,
    pattern: str,
    evidence: str,
) -> dict[str, str]:
    logger.info("Generating solution language=%s pattern=%s problem_chars=%s evidence_chars=%s", language, pattern, len(problem_text), len(evidence))
    raw = runtime.generate(solution_prompt(problem_text, language, pattern, evidence), max_new_tokens=4096, json_mode=True, schema_name="solution")
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


def generate_solution_variants(
    runtime: BaseModelRuntime,
    language: str,
    problem_text: str,
    pattern: str,
    evidence: str,
) -> list[dict[str, str]]:
    logger.info(
        "Generating solution variants language=%s pattern=%s problem_chars=%s evidence_chars=%s",
        language,
        pattern,
        len(problem_text),
        len(evidence),
    )
    variants: list[dict[str, str]] = []
    for approach_type in ("BRUTE_FORCE", "IMPROVED", "OPTIMAL"):
        raw = ""
        last_error: ValueError | None = None
        for attempt in range(1, 3):
            prompt = solution_variant_prompt(
                problem_text,
                language,
                pattern,
                evidence,
                approach_type,
                variants,
            )
            if attempt > 1:
                prompt += """

The previous candidate was invalid, truncated, or duplicated an earlier implementation. Generate a genuinely different algorithm, data structure, state representation, or control flow. Similar high-level intuition is acceptable when the implementation approach is distinct. Keep the explanation and pseudocode compact, keep the code complete, and return one complete JSON object only.
"""
            try:
                raw = runtime.generate(prompt, max_new_tokens=8192, json_mode=True, schema_name="solution")
                item = parse_json_object(raw)
                normalized = _normalize_solution_payload(item, pattern, language=language)
                normalized["approach_type"] = approach_type
                if any(_solutions_are_too_similar(normalized, existing) for existing in variants):
                    raise ValueError("Generated approach duplicates an earlier implementation.")
                variants.append(normalized)
                last_error = None
                break
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "Solution variant attempt rejected approach_type=%s attempt=%s error=%s response_preview=%s",
                    approach_type,
                    attempt,
                    exc,
                    response_preview(raw),
                )
        if last_error is not None:
            if approach_type == "IMPROVED":
                logger.warning("Skipping optional solution variant after retries approach_type=%s error=%s", approach_type, last_error)
                continue
            logger.error("Required solution variant failed after retries approach_type=%s error=%s", approach_type, last_error)
            raise last_error

    deduped = _dedupe_and_order_variants(variants)
    present_types = {variant["approach_type"] for variant in deduped}
    missing_required = {"BRUTE_FORCE", "OPTIMAL"} - present_types
    if missing_required:
        raise ValueError(f"Required solution variants are missing: {sorted(missing_required)}")
    logger.info(
        "Solution variants parsed count=%s approach_types=%s",
        len(deduped),
        [variant["approach_type"] for variant in deduped],
    )
    return deduped


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
        schema_name="solution",
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


def select_primary_solution(solutions: list[dict[str, str]]) -> dict[str, str]:
    if not solutions:
        raise ValueError("No solution variants available.")
    for preferred in ("OPTIMAL", "EXPECTED", "FINAL"):
        for solution in solutions:
            if solution.get("approach_type", "").upper() == preferred:
                return solution
    return solutions[-1]


def _dedupe_and_order_variants(variants: list[dict[str, str]]) -> list[dict[str, str]]:
    by_type: dict[str, dict[str, str]] = {}
    for variant in variants:
        approach = variant.get("approach_type", "FINAL").upper()
        variant["approach_type"] = _normalize_approach_type(approach)
        by_type.setdefault(variant["approach_type"], variant)
    ordered = sorted(by_type.values(), key=lambda item: APPROACH_ORDER.get(item["approach_type"], 10))
    return _remove_similar_variants(ordered)


def _remove_similar_variants(variants: list[dict[str, str]]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    skipped: list[str] = []
    for variant in variants:
        approach = variant.get("approach_type", "")
        if any(_solutions_are_too_similar(variant, existing) for existing in kept):
            skipped.append(approach)
            continue
        kept.append(variant)

    if skipped:
        logger.info("Dropped similar solution variants approach_types=%s", skipped)
    return sorted(kept, key=lambda item: APPROACH_ORDER.get(item["approach_type"], 10))


def _solutions_are_too_similar(left: dict[str, str], right: dict[str, str]) -> bool:
    same_complexity = (
        left.get("time_complexity", "").strip().lower() == right.get("time_complexity", "").strip().lower()
        and left.get("space_complexity", "").strip().lower() == right.get("space_complexity", "").strip().lower()
    )
    left_code = _code_fingerprint(left.get("code", ""))
    right_code = _code_fingerprint(right.get("code", ""))
    if not left_code or not right_code:
        return False
    if left_code == right_code:
        return True

    code_similarity = SequenceMatcher(None, left_code, right_code).ratio()
    if same_complexity and code_similarity >= 0.94:
        return True

    pseudocode_similarity = _token_similarity(left.get("pseudocode", ""), right.get("pseudocode", ""))
    if same_complexity and code_similarity >= 0.82 and pseudocode_similarity >= 0.82:
        return True

    same_pattern = _normalized_text(left.get("algorithm_pattern", "")) == _normalized_text(right.get("algorithm_pattern", ""))
    return same_pattern and code_similarity >= 0.75 and pseudocode_similarity >= 0.9


def _code_fingerprint(code: str) -> str:
    code = re.sub(r"//.*?$|/\*.*?\*/|#.*?$", "", code, flags=re.MULTILINE | re.DOTALL)
    code = re.sub(r"\s+", "", code)
    return code.lower()


def _token_similarity(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"[a-z0-9]+", left.lower()))
    right_tokens = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


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

    algorithm_pattern = _normalize_generated_text(
        field("algorithm_pattern", fallback_pattern),
        field_name="algorithm_pattern",
        max_length=MAX_ALGORITHM_PATTERN_LENGTH,
    )
    time_complexity = _normalize_generated_text(
        field("time_complexity", (previous_solution or {}).get("time_complexity", "Not specified.")),
        field_name="time_complexity",
        max_length=MAX_COMPLEXITY_DESCRIPTION_LENGTH,
    )
    space_complexity = _normalize_generated_text(
        field("space_complexity", (previous_solution or {}).get("space_complexity", "Not specified.")),
        field_name="space_complexity",
        max_length=MAX_COMPLEXITY_DESCRIPTION_LENGTH,
    )
    result = {
        "approach_type": _normalize_approach_type(field("approach_type", "FINAL")),
        "algorithm_pattern": algorithm_pattern,
        "explanation": field(
            "explanation",
            (previous_solution or {}).get("explanation", "Generated solution for the programming problem."),
        ),
        "pseudocode": field("pseudocode", _fallback_pseudocode(fallback_pattern)),
        "code": code,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
    }
    if defaults_used:
        logger.warning("Solution payload missing optional fields; defaults used fields=%s", defaults_used)
    return result


def _normalize_approach_type(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
    if normalized in {"AVERAGE", "BETTER", "INTERMEDIATE"}:
        return "IMPROVED"
    if normalized in {"EXPECTED", "FINAL", "BEST"}:
        return "OPTIMAL"
    if normalized in {"BRUTE", "NAIVE"}:
        return "BRUTE_FORCE"
    return normalized[:40] or "OPTIMAL"


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
