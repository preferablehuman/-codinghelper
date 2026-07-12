from functools import lru_cache

from pydantic import Field, model_validator
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
    qdrant_problem_collection: str = "problem_corpus"
    qdrant_knowledge_collection: str = "knowledge_chunks"
    sandbox_runner_url: str = "http://sandbox-runner:8100"
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
    rag_reuse_enabled: bool = True
    rag_external_discovery_enabled: bool = True
    rag_promote_successful_runs: bool = True
    rag_exact_reverify: bool = True
    rag_max_local_candidates: int = 10
    rag_max_external_candidates: int = 10
    rag_equivalent_threshold: float = 0.90
    rag_related_threshold: float = 0.72
    rag_min_asserting_tests: int = 8
    rag_semantic_weight: float = 0.45
    rag_lexical_weight: float = 0.20
    rag_constraint_weight: float = 0.15
    rag_io_weight: float = 0.10
    rag_objective_weight: float = 0.10
    enabled_retrieval_adapters: str = "stack_exchange,codeforces,curated_repository,user_url"
    stack_exchange_key: str = ""
    github_token: str = ""
    external_fetch_timeout_seconds: float = 10.0
    external_fetch_max_bytes: int = 2_000_000
    external_fetch_max_redirects: int = 3

    @model_validator(mode="after")
    def validate_retrieval_settings(self) -> "Settings":
        weights = (
            self.rag_semantic_weight,
            self.rag_lexical_weight,
            self.rag_constraint_weight,
            self.rag_io_weight,
            self.rag_objective_weight,
        )
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError("RAG scoring weights must be non-negative and sum to 1.0")
        if not 0 <= self.rag_related_threshold <= self.rag_equivalent_threshold <= 1:
            raise ValueError("RAG thresholds must satisfy 0 <= related <= equivalent <= 1")
        if self.rag_min_asserting_tests < 1:
            raise ValueError("RAG_MIN_ASSERTING_TESTS must be positive")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
