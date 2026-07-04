import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on", "debug"}


def configure_logging(service_name: str = "sandbox-runner") -> None:
    verbose = _truthy(os.getenv("VERBOSE_LOGGING"))
    level = logging.DEBUG if verbose else logging.INFO
    log_dir = Path(os.getenv("LOG_DIR", "/app/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    max_files = max(1, int(os.getenv("LOG_MAX_FILES", "10")))
    backup_count = max(0, max_files - 1)
    log_path = log_dir / f"{service_name}.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(process)d:%(threadName)s] %(name)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler._study_buddy_handler = True  # type: ignore[attr-defined]

    file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler._study_buddy_handler = True  # type: ignore[attr-defined]

    root_logger = logging.getLogger()
    root_logger.handlers = [
        handler for handler in root_logger.handlers if not getattr(handler, "_study_buddy_handler", False)
    ]
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(level)

    logging.captureWarnings(True)
    logging.getLogger(__name__).info(
        "Logging configured for %s at %s with max_bytes=%s max_files=%s verbose=%s",
        service_name,
        log_path,
        max_bytes,
        max_files,
        verbose,
    )
