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
    model_provider: str = "ollama"
    model_name_or_path: str = "qwen2.5-coder:7b"
    model_device: str = "auto"
    model_max_new_tokens: int = 2048
    model_temperature: float = 0.2
    model_lazy_load: bool = False
    model_require_cuda: bool = True
    model_allow_cpu_offload: bool = True
    model_allow_disk_offload: bool = False
    model_cache_dir: str = "/app/data/model-cache/huggingface"
    model_persistent_cache_root: str = "/app/data/model-cache"
    model_require_persistent_cache: bool = True
    model_download_on_startup: bool = True
    model_local_files_only: bool = False
    model_quantization: str = "auto"
    model_quantization_fallback: str = "8bit"
    model_load_in_4bit: bool = True
    model_load_log_interval_seconds: int = 30
    model_gpu_memory_limit: str = "9GiB"
    model_gpu_memory_utilization: float = 0.78
    model_kv_cache_vram_reserve: str = "2.5GiB"
    model_cpu_memory_limit: str = "24GiB"
    model_offload_dir: str = "/app/data/model-cache/offload"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_num_ctx: int = 8192
    ollama_num_gpu: int | None = None
    ollama_keep_alive: str = "-1"
    ollama_require_gpu: bool = True
    ollama_pull_on_startup: bool = False
    ollama_request_timeout_seconds: float = 600.0
    ollama_load_timeout_seconds: float = 1800.0
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
