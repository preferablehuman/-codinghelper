import logging

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.prompts import slide_markdown_prompt


logger = logging.getLogger(__name__)


def build_slide_markdown(
    runtime: BaseModelRuntime,
    title: str,
    problem_summary: str,
    pattern: str,
    solution: dict[str, object],
    explanation: dict[str, str],
    sources: list[dict[str, str]],
) -> str:
    logger.info(
        "Generating slide markdown title=%s pattern=%s source_count=%s",
        title,
        pattern,
        len(sources),
    )
    markdown = runtime.generate(
        slide_markdown_prompt(title, problem_summary, pattern, solution, explanation, sources),
        max_new_tokens=4096,
    ).strip()
    if not markdown:
        raise ValueError("Model did not generate slide markdown.")
    logger.info("Slide markdown generated chars=%s", len(markdown))
    return markdown
