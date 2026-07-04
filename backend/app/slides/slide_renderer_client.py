import logging
import time

import httpx

from app.config import get_settings


logger = logging.getLogger(__name__)


def render_slides(job_id: str, markdown: str) -> dict[str, str | None]:
    settings = get_settings()
    try:
        started = time.perf_counter()
        logger.info(
            "Calling slide renderer url=%s job_id=%s markdown_chars=%s",
            settings.slide_renderer_url,
            job_id,
            len(markdown),
        )
        response = httpx.post(
            f"{settings.slide_renderer_url}/render",
            json={"job_id": job_id, "markdown": markdown, "formats": ["html", "pptx"]},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Slide renderer response job_id=%s html_path=%s pptx_path=%s elapsed_ms=%s",
            job_id,
            result.get("html_path"),
            result.get("pptx_path"),
            elapsed_ms,
        )
        return result
    except Exception:
        logger.exception("Slide renderer call failed job_id=%s", job_id)
        return {"html_path": None, "pdf_path": None, "pptx_path": None}
