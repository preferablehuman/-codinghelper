import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.providers.base import ModelProvider


logger = logging.getLogger(__name__)


class GeminiProvider(ModelProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
        request_timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.temperature = temperature
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max(1, max_retries)
        self._status: dict[str, Any] = {
            "provider": "gemini",
            "model": self.model,
            "loaded": False,
            "remote": True,
        }

    def load(self) -> None:
        if not self.api_key:
            raise RuntimeError("The model gateway has no API key configured.")
        response = httpx.get(
            f"{self.base_url}/models/{quote(self.model, safe='')}",
            headers=self._headers(),
            timeout=min(self.request_timeout_seconds, 30.0),
        )
        self._raise_for_status(response, "Gemini model verification failed")
        model_info = response.json()
        self._status = {
            "provider": "gemini",
            "model": self.model,
            "display_name": model_info.get("displayName"),
            "loaded": True,
            "remote": True,
            "input_token_limit": model_info.get("inputTokenLimit"),
            "output_token_limit": model_info.get("outputTokenLimit"),
        }

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def generate(self, prompt: str, max_new_tokens: int, *, json_mode: bool = False) -> str:
        if not self._status.get("loaded"):
            self.load()
        generation_config: dict[str, Any] = {
            "temperature": self.temperature,
            "maxOutputTokens": max(1, max_new_tokens),
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        url = f"{self.base_url}/models/{quote(self.model, safe='')}:generateContent"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = httpx.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.request_timeout_seconds,
                )
                self._raise_for_status(response, "Gemini generation failed")
                return self._response_text(response.json())
            except (httpx.TimeoutException, httpx.NetworkError, RuntimeError) as exc:
                if attempt >= self.max_retries or not self._retryable(exc):
                    raise
                delay = min(2 ** (attempt - 1), 8)
                logger.warning("Retrying provider request attempt=%s delay_seconds=%s error=%s", attempt, delay, exc)
                time.sleep(delay)
        raise RuntimeError("Gemini generation exhausted all retry attempts.")

    def _headers(self) -> dict[str, str]:
        return {"content-type": "application/json", "x-goog-api-key": self.api_key}

    def _response_text(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            raise RuntimeError(f"Provider returned no response candidates{f' ({reason})' if reason else ''}.")
        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise RuntimeError("Provider returned an empty response.")
        return text

    def _raise_for_status(self, response: httpx.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"{message} ({response.status_code}): {response.text[:1200]}") from exc

    def _retryable(self, exc: Exception) -> bool:
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
            return True
        message = str(exc)
        return "(429)" in message or any(f"({status})" in message for status in range(500, 600))
