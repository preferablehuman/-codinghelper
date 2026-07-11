import logging
from functools import lru_cache

from app.config import get_settings
from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.gateway_runtime import ModelGatewayRuntime


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model_runtime() -> BaseModelRuntime:
    settings = get_settings()
    logger.info("Creating provider-neutral model gateway client base_url=%s", settings.model_gateway_url)
    return ModelGatewayRuntime(
        base_url=settings.model_gateway_url,
        request_timeout_seconds=settings.model_gateway_request_timeout_seconds,
        health_timeout_seconds=settings.model_gateway_health_timeout_seconds,
    )
