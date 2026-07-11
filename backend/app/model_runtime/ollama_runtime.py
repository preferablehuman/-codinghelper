"""Legacy reference only; active Ollama orchestration lives in model-gateway.

This module is intentionally not imported by the application runtime and can be
removed once the historical local-runtime migration is no longer needed.
"""

import logging
import time
from typing import Any

import httpx

from app.model_runtime.base import BaseModelRuntime


logger = logging.getLogger(__name__)


class OllamaModelRuntime(BaseModelRuntime):
    def __init__(
        self,
        base_url: str,
        model: str,
        max_new_tokens: int,
        temperature: float,
        num_ctx: int,
        keep_alive: str,
        require_gpu: bool,
        pull_on_startup: bool,
        request_timeout_seconds: float,
        load_timeout_seconds: float,
        num_gpu: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.num_gpu = num_gpu
        self.keep_alive = keep_alive
        self.require_gpu = require_gpu
        self.pull_on_startup = pull_on_startup
        self.request_timeout_seconds = request_timeout_seconds
        self.load_timeout_seconds = load_timeout_seconds
        self._loaded = False
        self._last_status: dict[str, Any] = {
            "provider": "ollama",
            "model": self.model,
            "loaded": False,
            "base_url": self.base_url,
        }

    def load(self) -> None:
        started = time.perf_counter()
        logger.info(
            (
                "Ollama model preload started base_url=%s model=%s num_ctx=%s num_gpu=%s "
                "keep_alive=%s require_gpu=%s pull_on_startup=%s"
            ),
            self.base_url,
            self.model,
            self.num_ctx,
            self.num_gpu,
            self.keep_alive,
            self.require_gpu,
            self.pull_on_startup,
        )
        self._wait_for_server()
        if self.pull_on_startup:
            self._pull_model()
        model_info = self._require_model_present()
        self._log_model_info("Ollama model available", model_info)
        warmup = self._generate_raw("Reply with OK only.", max_new_tokens=1, timeout_seconds=self.load_timeout_seconds)
        logger.info(
            (
                "Ollama warmup completed model=%s response_chars=%s total_duration_ns=%s "
                "load_duration_ns=%s prompt_tokens=%s eval_tokens=%s"
            ),
            self.model,
            len(str(warmup.get("response", ""))),
            warmup.get("total_duration"),
            warmup.get("load_duration"),
            warmup.get("prompt_eval_count"),
            warmup.get("eval_count"),
        )
        running_info = self._running_model_info()
        self._validate_gpu_residency(running_info)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._loaded = True
        self._last_status = self._build_status(model_info, running_info, elapsed_ms)
        logger.info("Ollama model preload completed elapsed_ms=%s status=%s", elapsed_ms, self._last_status)

    def status(self) -> dict[str, Any]:
        if not self._loaded:
            return dict(self._last_status)
        try:
            model_info = self._model_info()
            running_info = self._running_model_info()
            self._last_status = self._build_status(model_info, running_info)
        except Exception as exc:
            logger.warning("Ollama status refresh failed model=%s error=%s", self.model, exc)
        return dict(self._last_status)

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False) -> str:
        if not self._loaded:
            self.load()
        started = time.perf_counter()
        attempts = 2 if json_mode else 1
        last_text = ""
        for attempt in range(1, attempts + 1):
            logger.info(
                "Ollama generation started model=%s prompt_chars=%s max_new_tokens=%s num_ctx=%s json_mode=%s attempt=%s",
                self.model,
                len(prompt),
                max_new_tokens,
                self.num_ctx,
                json_mode,
                attempt,
            )
            result = self._generate_raw(
                prompt,
                max_new_tokens=max_new_tokens,
                timeout_seconds=self.request_timeout_seconds,
                json_mode=json_mode,
            )
            text = str(result.get("response", "")).strip()
            last_text = text
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                (
                    "Ollama generation completed model=%s elapsed_ms=%s response_chars=%s "
                    "prompt_tokens=%s eval_tokens=%s total_duration_ns=%s load_duration_ns=%s "
                    "eval_duration_ns=%s done=%s done_reason=%s attempt=%s"
                ),
                self.model,
                elapsed_ms,
                len(text),
                result.get("prompt_eval_count"),
                result.get("eval_count"),
                result.get("total_duration"),
                result.get("load_duration"),
                result.get("eval_duration"),
                result.get("done"),
                result.get("done_reason"),
                attempt,
            )
            if result.get("done") is False and attempt < attempts:
                logger.warning(
                    "Ollama returned a non-final generation response; retrying model=%s response_chars=%s attempt=%s",
                    self.model,
                    len(text),
                    attempt,
                )
                continue
            return text
        return last_text

    def _wait_for_server(self) -> None:
        deadline = time.monotonic() + self.load_timeout_seconds
        attempt = 0
        last_error: str | None = None
        while time.monotonic() < deadline:
            attempt += 1
            try:
                response = httpx.get(f"{self.base_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                logger.info("Ollama server is reachable base_url=%s attempts=%s", self.base_url, attempt)
                return
            except Exception as exc:
                last_error = str(exc)
                logger.info("Waiting for Ollama server base_url=%s attempt=%s error=%s", self.base_url, attempt, last_error)
                time.sleep(2)
        raise RuntimeError(f"Ollama server was not reachable at {self.base_url}: {last_error}")

    def _pull_model(self) -> None:
        started = time.perf_counter()
        logger.info("Ollama pull requested model=%s", self.model)
        response = httpx.post(
            f"{self.base_url}/api/pull",
            json={"model": self.model, "stream": False},
            timeout=self.load_timeout_seconds,
        )
        response.raise_for_status()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("Ollama pull completed model=%s elapsed_ms=%s response=%s", self.model, elapsed_ms, response.json())

    def _require_model_present(self) -> dict[str, Any]:
        model_info = self._model_info()
        if model_info:
            return model_info
        raise RuntimeError(
            f"Ollama model {self.model!r} is not present. The ollama service should pull it before backend startup."
        )

    def _model_info(self) -> dict[str, Any]:
        data = self._get_json("/api/tags", timeout_seconds=30.0)
        for model_info in data.get("models", []):
            if self._is_requested_model(model_info):
                return model_info
        return {}

    def _running_model_info(self) -> dict[str, Any]:
        data = self._get_json("/api/ps", timeout_seconds=30.0)
        for model_info in data.get("models", []):
            if self._is_requested_model(model_info):
                self._log_model_info("Ollama running model", model_info)
                return model_info
        return {}

    def _validate_gpu_residency(self, running_info: dict[str, Any]) -> None:
        if not self.require_gpu:
            return
        if not running_info:
            raise RuntimeError("OLLAMA_REQUIRE_GPU=true but the warmed model is not listed by /api/ps.")
        size_vram = int(running_info.get("size_vram") or 0)
        if size_vram <= 0:
            raise RuntimeError(
                "OLLAMA_REQUIRE_GPU=true but Ollama reports zero VRAM residency for the warmed model. "
                "Check Docker GPU access and NVIDIA runtime support."
            )
        size_total = int(running_info.get("size") or 0)
        if size_total and size_vram < size_total:
            logger.info(
                "Ollama is using partial CPU offload model=%s size_bytes=%s size_vram_bytes=%s cpu_or_ram_bytes=%s",
                self.model,
                size_total,
                size_vram,
                size_total - size_vram,
            )
        else:
            logger.info("Ollama model is resident in VRAM model=%s size_vram_bytes=%s", self.model, size_vram)

    def _generate_raw(
        self,
        prompt: str,
        max_new_tokens: int,
        timeout_seconds: float,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "num_predict": max_new_tokens,
            "temperature": self.temperature,
        }
        if self.num_ctx > 0:
            options["num_ctx"] = self.num_ctx
        if self.num_gpu is not None:
            options["num_gpu"] = self.num_gpu
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if json_mode:
            payload["format"] = "json"
        api_keep_alive = self._api_keep_alive()
        if api_keep_alive is not None:
            payload["keep_alive"] = api_keep_alive
        logger.debug(
            "Ollama generate request prepared model=%s prompt_chars=%s timeout_seconds=%s keep_alive_sent=%s json_mode=%s options=%s",
            self.model,
            len(prompt),
            timeout_seconds,
            api_keep_alive,
            json_mode,
            options,
        )
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=timeout_seconds,
        )
        self._raise_for_status(response, "Ollama generate request failed")
        return response.json()

    def _get_json(self, path: str, timeout_seconds: float) -> dict[str, Any]:
        response = httpx.get(f"{self.base_url}{path}", timeout=timeout_seconds)
        self._raise_for_status(response, f"Ollama GET {path} failed")
        return response.json()

    def _api_keep_alive(self) -> str | None:
        value = str(self.keep_alive or "").strip()
        if value.lower() in {"", "-1", "forever", "infinite", "infinity"}:
            return None
        return value

    def _raise_for_status(self, response: httpx.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(
                "%s status=%s url=%s response_body=%s",
                message,
                response.status_code,
                response.request.url,
                response.text[:2000],
            )
            raise

    def _is_requested_model(self, model_info: dict[str, Any]) -> bool:
        names = {
            str(model_info.get("name", "")),
            str(model_info.get("model", "")),
        }
        return self.model in names

    def _build_status(
        self,
        model_info: dict[str, Any],
        running_info: dict[str, Any],
        preload_elapsed_ms: int | None = None,
    ) -> dict[str, Any]:
        details = model_info.get("details") or {}
        running_details = running_info.get("details") or {}
        return {
            "provider": "ollama",
            "loaded": self._loaded,
            "model": self.model,
            "base_url": self.base_url,
            "format": details.get("format") or running_details.get("format"),
            "family": details.get("family") or running_details.get("family"),
            "parameter_size": details.get("parameter_size") or running_details.get("parameter_size"),
            "quantization_level": details.get("quantization_level") or running_details.get("quantization_level"),
            "size_bytes": model_info.get("size") or running_info.get("size"),
            "size_vram_bytes": running_info.get("size_vram"),
            "context_length": running_info.get("context_length"),
            "configured_num_ctx": self.num_ctx,
            "configured_num_gpu": self.num_gpu,
            "keep_alive": self.keep_alive,
            "require_gpu": self.require_gpu,
            "preload_elapsed_ms": preload_elapsed_ms,
        }

    def _log_model_info(self, message: str, model_info: dict[str, Any]) -> None:
        details = model_info.get("details") or {}
        logger.info(
            (
                "%s model=%s size_bytes=%s size_vram_bytes=%s context_length=%s "
                "format=%s family=%s parameters=%s quantization=%s digest=%s"
            ),
            message,
            model_info.get("name") or model_info.get("model") or self.model,
            model_info.get("size"),
            model_info.get("size_vram"),
            model_info.get("context_length"),
            details.get("format"),
            details.get("family"),
            details.get("parameter_size"),
            details.get("quantization_level"),
            model_info.get("digest"),
        )
