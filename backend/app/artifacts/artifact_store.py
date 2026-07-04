import logging
from pathlib import Path

from app.config import get_settings


logger = logging.getLogger(__name__)


def save_slide_markdown(job_id: str, markdown: str) -> str:
    settings = get_settings()
    job_dir = Path(settings.artifact_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    path = job_dir / "deck.md"
    path.write_text(markdown, encoding="utf-8")
    logger.info("Saved slide markdown job_id=%s path=%s chars=%s", job_id, path, len(markdown))
    return str(path)
