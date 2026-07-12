import logging
from typing import Any

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import parse_json_object
from app.model_runtime.prompts import slide_deck_prompt


logger = logging.getLogger(__name__)


ALLOWED_KINDS = {"title", "problem", "observation", "comparison", "approach", "state", "dry_run", "code", "correctness", "verification", "summary", "references"}


def build_slide_deck(
    runtime: BaseModelRuntime,
    title: str,
    problem_summary: str,
    pattern: str,
    solution: dict[str, object],
    explanation: dict[str, str],
    sources: list[dict[str, str]],
) -> dict[str, Any]:
    logger.info("Generating structured teaching deck title=%s pattern=%s source_count=%s", title, pattern, len(sources))
    raw = runtime.generate(
        slide_deck_prompt(title, problem_summary, pattern, solution, explanation, sources),
        max_new_tokens=8192,
        json_mode=True,
    )
    data = parse_json_object(raw, wrapper_keys=("deck", "presentation", "result", "data"))
    deck = _normalize_deck(data, title, problem_summary)
    logger.info("Structured teaching deck generated slide_count=%s", len(deck["slides"]))
    return deck


def deck_to_markdown(deck: dict[str, Any]) -> str:
    sections: list[str] = []
    for slide in deck.get("slides", []):
        lines = [f"# {slide['title']}", "", slide.get("takeaway", "")]
        lines.extend(f"- {bullet}" for bullet in slide.get("bullets", []))
        table = slide.get("table", {})
        headers = table.get("headers", []) if isinstance(table, dict) else []
        rows = table.get("rows", []) if isinstance(table, dict) else []
        if headers:
            lines.extend(["", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
            lines.extend("| " + " | ".join(row) + " |" for row in rows)
        if slide.get("code"):
            lines.extend(["", "```", slide["code"], "```"])
        sections.append("\n".join(lines).strip())
    return "\n\n---\n\n".join(sections)


def _normalize_deck(data: dict[str, Any], fallback_title: str, problem_summary: str) -> dict[str, Any]:
    raw_slides = data.get("slides")
    if not isinstance(raw_slides, list):
        raise ValueError("Teaching deck response must contain a slides array.")
    slides = [_normalize_slide(item, index) for index, item in enumerate(raw_slides) if isinstance(item, dict)]
    if len(slides) < 10:
        raise ValueError(f"Teaching deck must contain at least 10 substantive slides, got {len(slides)}.")
    slides = slides[:16]
    if slides[0]["kind"] != "title":
        slides.insert(0, _normalize_slide({"kind": "title", "title": fallback_title, "takeaway": problem_summary}, 0))
        slides = slides[:16]
    return {
        "deck_title": _text(data.get("deck_title"), fallback_title, 120),
        "audience": _text(data.get("audience"), "Beginner programming learner", 160),
        "learning_objective": _text(data.get("learning_objective"), f"Explain and implement {fallback_title}.", 240),
        "slides": slides,
    }


def _normalize_slide(item: dict[str, Any], index: int) -> dict[str, Any]:
    kind = str(item.get("kind") or ("title" if index == 0 else "approach")).strip().lower()
    if kind not in ALLOWED_KINDS:
        kind = "approach"
    table = item.get("table") if isinstance(item.get("table"), dict) else {}
    headers = [_text(value, "", 40) for value in table.get("headers", []) if str(value).strip()][:6]
    rows = [
        [_text(value, "", 70) for value in row[: len(headers) or 6]]
        for row in table.get("rows", [])
        if isinstance(row, list)
    ][:8]
    return {
        "kind": kind,
        "title": _text(item.get("title"), f"Step {index + 1}", 90),
        "takeaway": _text(item.get("takeaway"), "", 260),
        "bullets": [_text(value, "", 180) for value in item.get("bullets", []) if str(value).strip()][:5],
        "flow": [_text(value, "", 55) for value in item.get("flow", []) if str(value).strip()][:5],
        "code": _text(item.get("code"), "", 3000, collapse=False),
        "table": {"headers": headers, "rows": rows},
        "notes": _text(item.get("notes"), "", 1800, collapse=False),
    }


def _text(value: object, default: str, limit: int, *, collapse: bool = True) -> str:
    text = str(value).strip() if value is not None else default
    if collapse:
        text = " ".join(text.split())
    return text[:limit]
