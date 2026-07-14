import logging
import json
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.providers.base import ModelProvider


logger = logging.getLogger(__name__)
SUPPORTED_PROVIDERS = {"nvidia", "gemini", "ollama", "openai", "openai_compatible"}


@dataclass(frozen=True)
class ProviderConfiguration:
    model: str
    json_model: str
    api_key: str
    base_url: str


def provider_configuration(settings: Settings, provider: str) -> ProviderConfiguration:
    prefix = provider.strip().lower().replace("-", "_")
    if prefix not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported LangChain provider: {provider!r}")
    return ProviderConfiguration(
        model=str(getattr(settings, f"{prefix}_llm_model")).strip(),
        json_model=str(getattr(settings, f"{prefix}_llm_json_model")).strip(),
        api_key=str(getattr(settings, f"{prefix}_llm_api_key", "")).strip(),
        base_url=str(getattr(settings, f"{prefix}_llm_base_url")).strip(),
    )


class LangChainProvider(ModelProvider):
    @classmethod
    def from_settings(cls, settings: Settings) -> "LangChainProvider":
        provider = settings.llm_provider.strip().lower().replace("-", "_")
        selected = provider_configuration(settings, provider)
        return cls(
            provider=provider,
            model=selected.model,
            json_model=selected.json_model,
            api_key=selected.api_key,
            base_url=selected.base_url,
            temperature=settings.llm_temperature,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=settings.llm_max_retries,
            ollama_num_ctx=settings.ollama_num_ctx,
            ollama_keep_alive=settings.ollama_keep_alive,
        )

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        json_model: str,
        api_key: str,
        base_url: str,
        temperature: float,
        request_timeout_seconds: float,
        max_retries: int,
        ollama_num_ctx: int,
        ollama_keep_alive: str,
    ) -> None:
        self.provider = provider
        self.model = model.strip()
        self.json_model = json_model.strip() or self.model
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max(1, max_retries)
        self.ollama_num_ctx = ollama_num_ctx
        self.ollama_keep_alive = ollama_keep_alive
        self._status: dict[str, Any] = {
            "provider": provider,
            "model": self.model,
            "json_model": self.json_model,
            "framework": "langchain",
            "loaded": False,
            "remote": provider != "ollama",
        }

    def load(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported LangChain provider: {self.provider!r}")
        if not self.model:
            raise RuntimeError("No LLM model is configured.")
        if self.provider != "ollama" and not self.api_key:
            raise RuntimeError(f"No API key is configured for provider {self.provider!r}.")
        # Constructing both clients validates integration packages and configuration
        # without spending tokens or making backend startup depend on inference.
        self._build_chat_model(self.model, max_new_tokens=1024, json_mode=False)
        if self.json_model != self.model:
            self._build_chat_model(self.json_model, max_new_tokens=1024, json_mode=True)
        self._status = {
            **self._status,
            "loaded": True,
            "display_name": self.model,
            "json_model_display_name": self.json_model,
        }
        logger.info("LangChain model adapter ready provider=%s model=%s json_model=%s", self.provider, self.model, self.json_model)

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def generate(self, prompt: str, max_new_tokens: int, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        if not self._status.get("loaded"):
            self.load()
        request_model = self.json_model if json_mode else self.model
        chat_model = self._build_chat_model(request_model, max_new_tokens=max_new_tokens, json_mode=json_mode, schema_name=schema_name)
        runnable = chat_model
        structured_runnable = False
        if json_mode and schema_name:
            from app.structured_schemas import schema_model_for

            schema_model = schema_model_for(schema_name)
            if schema_model is not None:
                runnable = chat_model.with_structured_output(schema_model)
                structured_runnable = True
        runnable = runnable.with_retry(
            retry_if_exception_type=(Exception,),
            wait_exponential_jitter=True,
            stop_after_attempt=self.max_retries,
        )
        try:
            response = runnable.invoke(prompt)
        except Exception:
            if not structured_runnable:
                raise
            logger.warning(
                "Provider-native structured output failed; falling back to JSON-mode generation provider=%s schema=%s",
                self.provider,
                schema_name,
                exc_info=True,
            )
            response = chat_model.with_retry(
                retry_if_exception_type=(Exception,),
                wait_exponential_jitter=True,
                stop_after_attempt=self.max_retries,
            ).invoke(prompt)
        if hasattr(response, "model_dump"):
            return json.dumps(response.model_dump(), ensure_ascii=False, separators=(",", ":"))
        if isinstance(response, (dict, list)):
            return json.dumps(response, ensure_ascii=False, separators=(",", ":"))
        text = _message_text(response)
        if not text:
            raise RuntimeError("LangChain model returned an empty response.")
        return text

    def _build_chat_model(self, model: str, *, max_new_tokens: int, json_mode: bool, schema_name: str | None = None):
        if self.provider == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            kwargs: dict[str, Any] = {
                "model": model,
                "temperature": self.temperature,
                "max_tokens": max_new_tokens,
                "timeout": self.request_timeout_seconds,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            return ChatNVIDIA(**kwargs)

        if self.provider == "ollama":
            from langchain_ollama import ChatOllama

            kwargs = {
                "model": model,
                "base_url": self.base_url or "http://ollama:11434",
                "temperature": self.temperature,
                "num_predict": max_new_tokens,
                "num_ctx": self.ollama_num_ctx,
                "keep_alive": self.ollama_keep_alive,
                "client_kwargs": {"timeout": self.request_timeout_seconds},
            }
            if json_mode:
                from app.structured_schemas import schema_for
                kwargs["format"] = schema_for(schema_name) or "json"
            return ChatOllama(**kwargs)

        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            kwargs = {
                "model": model,
                "api_key": self.api_key,
                "temperature": self.temperature,
                "max_output_tokens": max_new_tokens,
                "timeout": self.request_timeout_seconds,
                "max_retries": 0,
            }
            model_instance = ChatGoogleGenerativeAI(**kwargs)
            if json_mode and model.lower().startswith("gemini"):
                return model_instance.bind(response_mime_type="application/json")
            return model_instance

        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": max_new_tokens,
            "timeout": self.request_timeout_seconds,
            "max_retries": 0,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        model_instance = ChatOpenAI(**kwargs)
        if json_mode:
            return model_instance.bind(response_format={"type": "json_object"})
        return model_instance


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return str(content or "").strip()

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type", "")).lower()
        if block_type in {"reasoning", "thinking", "thought"}:
            continue
        text = block.get("text") or block.get("content")
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts).strip()
