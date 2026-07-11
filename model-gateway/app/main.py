import logging

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.provider import get_provider
from app.schemas import GenerateRequest, GenerateResponse


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="Study Buddy Model Gateway", version="1.0.0")
startup_error: str | None = None


def public_error(exc: Exception) -> str:
    message = str(exc)
    if "(401)" in message or "UNAUTHENTICATED" in message or "ACCESS_TOKEN_TYPE_UNSUPPORTED" in message:
        return "Model provider authentication failed. Replace or repair the gateway API credential."
    if "(429)" in message:
        return "Model provider quota is temporarily exhausted. Retry after the provider limit resets."
    if "API key" in message or "no API key" in message:
        return "No model provider credential is configured in the gateway."
    return f"Model provider is unavailable: {exc.__class__.__name__}."


@app.on_event("startup")
def initialize_provider() -> None:
    global startup_error
    try:
        get_provider().load()
        startup_error = None
        logger.info("Model provider is ready status=%s", get_provider().status())
    except Exception as exc:
        startup_error = public_error(exc)
        logger.warning("Model gateway started in degraded mode public_error=%s internal_error=%s", startup_error, exc)


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    try:
        model_status = get_provider().status()
    except Exception as exc:
        model_status = {"loaded": False, "error": f"{exc.__class__.__name__}: {exc}"}
    ready = bool(model_status.get("loaded"))
    return {
        "status": "ok" if ready else "degraded",
        "service": "model-gateway",
        "ready": ready,
        "provider": settings.llm_provider,
        "model": model_status,
        "error": None if ready else startup_error,
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    global startup_error
    provider = get_provider()
    try:
        text = provider.generate(request.prompt, request.max_new_tokens, json_mode=request.json_mode)
        startup_error = None
    except Exception as exc:
        startup_error = public_error(exc)
        logger.exception("Provider generation failed")
        raise HTTPException(status_code=503, detail=startup_error) from exc
    status = provider.status()
    return GenerateResponse(
        text=text,
        provider=str(status.get("provider", "unknown")),
        model=str(status.get("model", "unknown")),
    )
