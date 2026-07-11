from typing import Any

import httpx

from app.providers.base import ModelProvider


class OllamaProvider(ModelProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float,
        request_timeout_seconds: float,
        num_ctx: int,
        keep_alive: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.request_timeout_seconds = request_timeout_seconds
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self._status: dict[str, Any] = {
            "provider": "ollama",
            "model": model,
            "loaded": False,
            "remote": False,
        }

    def load(self) -> None:
        response = httpx.get(f"{self.base_url}/api/tags", timeout=min(self.request_timeout_seconds, 30.0))
        response.raise_for_status()
        models = response.json().get("models", [])
        model_info = next(
            (item for item in models if self.model in {str(item.get("name", "")), str(item.get("model", ""))}),
            None,
        )
        if not model_info:
            raise RuntimeError(f"Configured Ollama model {self.model!r} is not installed.")
        self._status = {
            "provider": "ollama",
            "model": self.model,
            "loaded": True,
            "remote": False,
            "details": model_info.get("details") or {},
        }

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def generate(self, prompt: str, max_new_tokens: int, *, json_mode: bool = False) -> str:
        if not self._status.get("loaded"):
            self.load()
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": max_new_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        if json_mode:
            payload["format"] = "json"
        if self.keep_alive.strip().lower() not in {"", "-1", "forever", "infinite", "infinity"}:
            payload["keep_alive"] = self.keep_alive
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        text = str(response.json().get("response", "")).strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response.")
        return text
