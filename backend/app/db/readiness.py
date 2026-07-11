import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings


logger = logging.getLogger(__name__)


def wait_for_database(timeout_seconds: float = 120.0, interval_seconds: float = 2.0) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    last_error: Exception | None = None
    try:
        while time.monotonic() < deadline:
            attempt += 1
            try:
                with engine.connect() as connection:
                    connection.execute(text("select 1"))
                logger.info("Database readiness check passed attempt=%s", attempt)
                return
            except SQLAlchemyError as exc:
                last_error = exc
                logger.warning(
                    "Database is not ready attempt=%s retry_in_seconds=%s error=%s",
                    attempt,
                    interval_seconds,
                    exc.__class__.__name__,
                )
                time.sleep(interval_seconds)
    finally:
        engine.dispose()
    raise RuntimeError(f"Database did not become ready within {timeout_seconds:.0f} seconds: {last_error}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    wait_for_database()
