from functools import lru_cache

from app.config import get_settings
from app.providers.base import ModelProvider


@lru_cache(maxsize=1)
def get_provider() -> ModelProvider:
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        from app.providers.gemini import GeminiProvider

        return GeminiProvider(
            api_key=settings.llm_api_key or settings.gemini_api_key,
            base_url=settings.llm_base_url or settings.gemini_base_url,
            model=settings.llm_model or settings.gemini_model,
            temperature=settings.llm_temperature,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if provider == "ollama":
        from app.providers.ollama import OllamaProvider

        return OllamaProvider(
            base_url=settings.llm_base_url or settings.ollama_base_url,
            model=settings.llm_model or settings.ollama_model,
            temperature=settings.llm_temperature,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
            num_ctx=settings.ollama_num_ctx,
            keep_alive=settings.ollama_keep_alive,
        )
    raise ValueError(f"Unsupported LLM provider: {provider!r}")
