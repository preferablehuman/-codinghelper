from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db.session import SessionLocal
from app.model_runtime.provider import get_model_runtime

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    database = "unknown"
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
        database = "ok"
    except Exception as exc:  # pragma: no cover - health should report, not crash
        database = f"error: {exc.__class__.__name__}"

    settings = get_settings()
    try:
        model_status: dict[str, object] = get_model_runtime().status()
    except Exception as exc:  # pragma: no cover - health should report, not crash
        model_status = {
            "loaded": False,
            "error": f"{exc.__class__.__name__}: {exc}",
        }

    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "backend",
        "environment": settings.app_env,
        "database": database,
        "model_provider": model_status.get("provider", "gateway"),
        "model_gateway": settings.model_gateway_url,
        "model_startup_load_required": False,
        "model": model_status,
    }
