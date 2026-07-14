import json
import re
from typing import Any


class StructuredOutputError(RuntimeError):
    pass


def normalize_json_text(text: str) -> str:
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        value: Any = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError("Model provider returned malformed structured output.") from exc

    if not isinstance(value, (dict, list)):
        raise StructuredOutputError("Model provider returned a JSON scalar instead of an object or array.")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def strict_json_retry_prompt(original_prompt: str, invalid_response: str) -> str:
    response_excerpt = invalid_response.strip()[:12_000]
    return f"""{original_prompt}

CRITICAL STRUCTURED-OUTPUT RETRY:
Your previous response violated the API contract. Convert its useful content into the exact JSON object or array requested above.
Do not include analysis, bullet points, headings, commentary, or Markdown fences before or after the JSON.
Use valid JSON escaping inside code and multiline string fields. Ensure every quote, bracket, and brace is closed.

INVALID PREVIOUS RESPONSE TO REFORMAT:
{response_excerpt}
"""
