import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import get_settings


def configure_logging(service_name: str = "backend") -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.verbose_logging else logging.INFO
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    max_files = max(1, settings.log_max_files)
    backup_count = max(0, max_files - 1)
    log_path = log_dir / f"{service_name}.log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(process)d:%(threadName)s] %(name)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler._study_buddy_handler = True  # type: ignore[attr-defined]

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
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

    noisy_library_levels = {
        "sqlalchemy": logging.INFO if settings.verbose_logging else logging.WARNING,
        "sqlalchemy.engine": logging.INFO if settings.verbose_logging else logging.WARNING,
        "sqlalchemy.pool": logging.DEBUG if settings.verbose_logging else logging.WARNING,
        "httpx": logging.DEBUG if settings.verbose_logging else logging.WARNING,
        "httpcore": logging.DEBUG if settings.verbose_logging else logging.WARNING,
        "accelerate": logging.DEBUG if settings.verbose_logging else logging.INFO,
        "bitsandbytes": logging.DEBUG if settings.verbose_logging else logging.INFO,
        "huggingface_hub": logging.DEBUG if settings.verbose_logging else logging.INFO,
        "transformers": logging.DEBUG if settings.verbose_logging else logging.INFO,
    }

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(level if settings.verbose_logging else logging.INFO)

    for logger_name, logger_level in noisy_library_levels.items():
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(logger_level)

    logging.captureWarnings(True)
    logging.getLogger(__name__).info(
        "Logging configured for %s at %s with max_bytes=%s max_files=%s verbose=%s",
        service_name,
        log_path,
        settings.log_max_bytes,
        max_files,
        settings.verbose_logging,
    )
