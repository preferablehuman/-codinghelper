import logging
from functools import lru_cache

from app.config import get_settings
from app.model_runtime.base import BaseModelRuntime


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model_runtime() -> BaseModelRuntime:
    settings = get_settings()
    if settings.model_provider == "ollama":
        from app.model_runtime.ollama_runtime import OllamaModelRuntime

        model = settings.ollama_model or settings.model_name_or_path
        logger.info(
            (
                "Creating model runtime provider=%s model=%s base_url=%s num_ctx=%s num_gpu=%s "
                "keep_alive=%s require_gpu=%s pull_on_startup=%s"
            ),
            settings.model_provider,
            model,
            settings.ollama_base_url,
            settings.ollama_num_ctx,
            settings.ollama_num_gpu,
            settings.ollama_keep_alive,
            settings.ollama_require_gpu,
            settings.ollama_pull_on_startup,
        )
        return OllamaModelRuntime(
            base_url=settings.ollama_base_url,
            model=model,
            max_new_tokens=settings.model_max_new_tokens,
            temperature=settings.model_temperature,
            num_ctx=settings.ollama_num_ctx,
            num_gpu=settings.ollama_num_gpu,
            keep_alive=settings.ollama_keep_alive,
            require_gpu=settings.ollama_require_gpu,
            pull_on_startup=settings.ollama_pull_on_startup,
            request_timeout_seconds=settings.ollama_request_timeout_seconds,
            load_timeout_seconds=settings.ollama_load_timeout_seconds,
        )
    if settings.model_provider != "transformers":
        raise ValueError("MODEL_PROVIDER must be either 'ollama' or 'transformers'.")

    from app.model_runtime.transformers_runtime import TransformersModelRuntime

    logger.info(
        (
            "Creating model runtime provider=%s model=%s device=%s quantization=%s quantization_fallback=%s "
            "legacy_four_bit=%s require_cuda=%s "
            "allow_cpu_offload=%s allow_disk_offload=%s cache_dir=%s persistent_cache_root=%s "
            "download_on_startup=%s local_files_only=%s gpu_memory_limit=%s gpu_memory_utilization=%s "
            "kv_cache_vram_reserve=%s cpu_memory_limit=%s"
        ),
        settings.model_provider,
        settings.model_name_or_path,
        settings.model_device,
        settings.model_quantization,
        settings.model_quantization_fallback,
        settings.model_load_in_4bit,
        settings.model_require_cuda,
        settings.model_allow_cpu_offload,
        settings.model_allow_disk_offload,
        settings.model_cache_dir,
        settings.model_persistent_cache_root,
        settings.model_download_on_startup,
        settings.model_local_files_only,
        settings.model_gpu_memory_limit,
        settings.model_gpu_memory_utilization,
        settings.model_kv_cache_vram_reserve,
        settings.model_cpu_memory_limit,
    )
    return TransformersModelRuntime(
        model_name_or_path=settings.model_name_or_path,
        device=settings.model_device,
        max_new_tokens=settings.model_max_new_tokens,
        temperature=settings.model_temperature,
        cache_dir=settings.model_cache_dir,
        persistent_cache_root=settings.model_persistent_cache_root,
        require_persistent_cache=settings.model_require_persistent_cache,
        download_on_startup=settings.model_download_on_startup,
        local_files_only=settings.model_local_files_only,
        quantization=settings.model_quantization,
        quantization_fallback=settings.model_quantization_fallback,
        load_in_4bit=settings.model_load_in_4bit,
        load_log_interval_seconds=settings.model_load_log_interval_seconds,
        gpu_memory_limit=settings.model_gpu_memory_limit,
        gpu_memory_utilization=settings.model_gpu_memory_utilization,
        kv_cache_vram_reserve=settings.model_kv_cache_vram_reserve,
        cpu_memory_limit=settings.model_cpu_memory_limit,
        offload_dir=settings.model_offload_dir,
        require_cuda=settings.model_require_cuda,
        allow_cpu_offload=settings.model_allow_cpu_offload,
        allow_disk_offload=settings.model_allow_disk_offload,
    )
