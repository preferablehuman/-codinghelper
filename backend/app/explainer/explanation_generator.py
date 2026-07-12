import logging

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_object, response_preview
from app.model_runtime.prompts import explanation_prompt


logger = logging.getLogger(__name__)


def build_explanation(
    runtime: BaseModelRuntime,
    problem_summary: str,
    pattern: str,
    solution: dict[str, object],
    evidence: str,
    verification: dict[str, object],
) -> dict[str, str]:
    logger.info(
        "Generating explanation pattern=%s solution_code_chars=%s verification_status=%s",
        pattern,
        len(solution.get("code", "")),
        verification.get("status"),
    )
    base_prompt = explanation_prompt(problem_summary, pattern, solution, evidence, verification)
    raw = ""
    parse_error: ValueError | None = None
    for attempt in range(1, 3):
        prompt = base_prompt
        if attempt > 1:
            prompt += """

Your previous response was truncated or malformed. Return exactly one complete JSON object with all six requested fields. Shorten the prose and use compact dry-run tables so the JSON closes within the output limit. Do not wrap the object in an array or Markdown fence.
"""
        raw = runtime.generate(prompt, max_new_tokens=8192, json_mode=True)
        try:
            data = parse_json_object(raw, wrapper_keys=("explanation", "result", "data"))
            break
        except ValueError as exc:
            parse_error = exc
            log = logger.warning if attempt == 1 else logger.error
            log(
                "Explanation JSON parse failed attempt=%s response_chars=%s response_preview=%s",
                attempt,
                len(raw),
                response_preview(raw),
            )
    else:
        assert parse_error is not None
        raise parse_error
    defaults_used: list[str] = []

    def field(key: str, default: str) -> str:
        value = optional_string(data, key)
        if value:
            return value
        defaults_used.append(key)
        return default

    result = {
        "intuition": field("intuition", "Use the selected pattern to organize the important state and avoid brute force work."),
        "brute_force": field("brute_force", "A direct brute-force approach checks candidates without reusing prior work."),
        "optimized_approach": field("optimized_approach", str(solution.get("explanation", "Use the generated solution approach."))),
        "dry_run": field("dry_run", "Walk through the sample input while tracking the key state changes."),
        "pitfalls": field("pitfalls", "Watch input parsing, boundary cases, and duplicate or missing values."),
        "complexity_analysis": field("complexity_analysis", str(solution.get("time_complexity", "See solution complexity."))),
    }
    if defaults_used:
        logger.warning("Explanation payload missing optional fields; defaults used fields=%s", defaults_used)
    logger.info("Explanation payload parsed dry_run_chars=%s pitfalls_chars=%s", len(result["dry_run"]), len(result["pitfalls"]))
    return result
