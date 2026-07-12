from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "nvidia"
    llm_temperature: float = 0.2
    llm_request_timeout_seconds: float = 180.0
    llm_max_retries: int = 3

    nvidia_llm_model: str = ""
    nvidia_llm_json_model: str = ""
    nvidia_llm_api_key: str = ""
    nvidia_llm_base_url: str = "https://integrate.api.nvidia.com/v1"

    gemini_llm_model: str = "gemini-2.5-flash"
    gemini_llm_json_model: str = ""
    gemini_llm_api_key: str = ""
    gemini_llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    ollama_llm_model: str = "qwen2.5-coder:7b"
    ollama_llm_json_model: str = ""
    ollama_llm_base_url: str = "http://ollama:11434"
    ollama_num_ctx: int = 8192
    ollama_keep_alive: str = "-1"

    openai_llm_model: str = ""
    openai_llm_json_model: str = ""
    openai_llm_api_key: str = ""
    openai_llm_base_url: str = ""

    openai_compatible_llm_model: str = ""
    openai_compatible_llm_json_model: str = ""
    openai_compatible_llm_api_key: str = ""
    openai_compatible_llm_base_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
