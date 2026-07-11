from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    verbose_logging: bool = False
    log_dir: str = "/app/logs"
    log_max_bytes: int = 10_485_760
    log_max_files: int = 10
    database_url: str = Field(default="postgresql+psycopg://explainer:explainer@postgres:5432/programming_explainer")
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "sources"
    sandbox_runner_url: str = "http://sandbox-runner:8100"
    slide_renderer_url: str = "http://slide-renderer:8200"
    model_gateway_url: str = "http://model-gateway:8300"
    model_gateway_request_timeout_seconds: float = 660.0
    model_gateway_health_timeout_seconds: float = 10.0
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_allow_remote_download: bool = True
    embedding_cache_dir: str = "/app/data/model-cache/sentence-transformers"
    source_cache_dir: str = "/app/data/source-cache"
    artifact_dir: str = "/app/data/artifacts"
    enable_geeksforgeeks: bool = True
    enable_stack_exchange: bool = True
    enable_codeforces: bool = True
    enable_the_algorithms: bool = True
    enable_cp_algorithms: bool = True
    max_sources_per_job: int = 10
    max_chunks_per_source: int = 8
    max_repair_attempts: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
