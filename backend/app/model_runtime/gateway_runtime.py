import logging
from typing import Any

import httpx

from app.model_runtime.base import BaseModelRuntime


logger = logging.getLogger(__name__)


class ModelGatewayRuntime(BaseModelRuntime):
    """Provider-neutral client for the independent model gateway service."""

    def __init__(self, base_url: str, request_timeout_seconds: float, health_timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds
        self.health_timeout_seconds = health_timeout_seconds
        self._last_status: dict[str, Any] = {
            "loaded": False,
            "gateway": self.base_url,
            "error": "Model gateway has not been checked yet.",
        }

    def load(self) -> None:
        status = self._fetch_health()
        self._last_status = self._normalize_status(status)
        if not status.get("ready"):
            detail = status.get("error") or "The configured model provider is not ready."
            raise RuntimeError(str(detail))

    def status(self) -> dict[str, Any]:
        try:
            self._last_status = self._normalize_status(self._fetch_health())
        except Exception as exc:
            self._last_status = {
                **self._last_status,
                "loaded": False,
                "gateway": self.base_url,
                "error": f"Model gateway unavailable: {exc.__class__.__name__}",
            }
        return dict(self._last_status)

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        payload: dict[str, object] = {
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "json_mode": json_mode,
        }
        if schema_name is not None:
            payload["schema_name"] = schema_name
        response = httpx.post(
            f"{self.base_url}/generate",
            json=payload,
            timeout=self.request_timeout_seconds,
        )
        self._raise_for_status(response, "Model gateway generation failed")
        data = response.json()
        text = str(data.get("text", "")).strip()
        if not text:
            raise RuntimeError("Model gateway returned an empty response.")
        self._last_status = {
            **self._last_status,
            "loaded": True,
            "provider": data.get("provider"),
            "model": data.get("model"),
            "error": None,
        }
        return text

    def _fetch_health(self) -> dict[str, Any]:
        response = httpx.get(f"{self.base_url}/health", timeout=self.health_timeout_seconds)
        self._raise_for_status(response, "Model gateway health check failed")
        return response.json()

    def _normalize_status(self, gateway_status: dict[str, Any]) -> dict[str, Any]:
        model = gateway_status.get("model") if isinstance(gateway_status.get("model"), dict) else {}
        return {
            **model,
            "loaded": bool(gateway_status.get("ready")),
            "provider": model.get("provider") or gateway_status.get("provider"),
            "gateway": self.base_url,
            "gateway_status": gateway_status.get("status"),
            "error": gateway_status.get("error") or model.get("error"),
        }

    def _raise_for_status(self, response: httpx.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:1600]
            logger.error("%s status=%s response_body=%s", message, response.status_code, body)
            raise RuntimeError(f"{message} ({response.status_code}): {body}") from exc
