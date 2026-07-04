import logging
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

import torch

from app.model_runtime.base import BaseModelRuntime


logger = logging.getLogger(__name__)


class TransformersModelRuntime(BaseModelRuntime):
    def __init__(
        self,
        model_name_or_path: str,
        device: str,
        max_new_tokens: int,
        temperature: float,
        cache_dir: str | None = None,
        persistent_cache_root: str | None = None,
        require_persistent_cache: bool = True,
        download_on_startup: bool = True,
        local_files_only: bool = False,
        quantization: str | None = "auto",
        quantization_fallback: str | None = "8bit",
        load_in_4bit: bool = False,
        load_log_interval_seconds: int = 30,
        gpu_memory_limit: str | None = None,
        gpu_memory_utilization: float = 0.78,
        kv_cache_vram_reserve: str | None = None,
        cpu_memory_limit: str | None = None,
        offload_dir: str | None = None,
        require_cuda: bool = True,
        allow_cpu_offload: bool = False,
        allow_disk_offload: bool = False,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.cache_dir = cache_dir
        self.persistent_cache_root = persistent_cache_root
        self.require_persistent_cache = require_persistent_cache
        self.download_on_startup = download_on_startup
        self.local_files_only = local_files_only
        self.quantization = quantization
        self.quantization_fallback = quantization_fallback
        self.load_in_4bit = load_in_4bit
        self.load_log_interval_seconds = max(5, load_log_interval_seconds)
        self.gpu_memory_limit = gpu_memory_limit
        self.gpu_memory_utilization = gpu_memory_utilization
        self.kv_cache_vram_reserve = kv_cache_vram_reserve
        self.cpu_memory_limit = cpu_memory_limit
        self.offload_dir = offload_dir
        self.require_cuda = require_cuda
        self.allow_cpu_offload = allow_cpu_offload
        self.allow_disk_offload = allow_disk_offload
        self._tokenizer = None
        self._model = None
        self._load_lock = threading.Lock()
        self._generate_lock = threading.Lock()
        self._load_elapsed_ms: int | None = None
        self._load_kwargs_summary: dict[str, Any] = {}
        self._last_placement_status: dict[str, Any] | None = None
        self._snapshot_path: str | None = None
        self._active_quantization: str | None = None
        self._quantization_attempts: list[dict[str, Any]] = []

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        return "cuda" if torch.cuda.is_available() else "cpu"

    def load(self) -> None:
        self._load()

    def status(self) -> dict[str, Any]:
        loaded = self._model is not None and self._tokenizer is not None
        placement = self._last_placement_status
        if loaded and placement is None:
            placement = self._device_placement_status()
        return {
            "provider": "transformers",
            "model": self.model_name_or_path,
            "configured_device": self.device,
            "resolved_device": self._resolve_device(),
            "loaded": loaded,
            "require_cuda": self.require_cuda,
            "allow_cpu_offload": self.allow_cpu_offload,
            "allow_disk_offload": self.allow_disk_offload,
            "memory_plan": self._memory_plan_status(),
            "download_on_startup": self.download_on_startup,
            "local_files_only": self.local_files_only,
            "quantization": self.quantization,
            "quantization_fallback": self.quantization_fallback,
            "active_quantization": self._active_quantization,
            "quantization_attempts": self._quantization_attempts,
            "load_in_4bit": self.load_in_4bit,
            "cache_dir": self.cache_dir,
            "persistent_cache_root": self.persistent_cache_root,
            "cache_mount": self._cache_mount_status(),
            "snapshot_path": self._snapshot_path,
            "load_elapsed_ms": self._load_elapsed_ms,
            "load_options": self._load_kwargs_summary,
            "cuda": self._cuda_status(),
            "placement": placement,
        }

    def _load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        with self._load_lock:
            if self._model is not None and self._tokenizer is not None:
                return
            started = time.perf_counter()
            resolved_device = self._resolve_device()
            logger.info(
                (
                    "Transformers model load requested model=%s configured_device=%s resolved_device=%s "
                    "quantization=%s quantization_fallback=%s legacy_four_bit=%s require_cuda=%s "
                    "allow_cpu_offload=%s allow_disk_offload=%s cache_dir=%s "
                    "persistent_cache_root=%s download_on_startup=%s local_files_only=%s gpu_memory_limit=%s "
                    "gpu_memory_utilization=%s kv_cache_vram_reserve=%s cpu_memory_limit=%s offload_dir=%s"
                ),
                self.model_name_or_path,
                self.device,
                resolved_device,
                self.quantization,
                self.quantization_fallback,
                self.load_in_4bit,
                self.require_cuda,
                self.allow_cpu_offload,
                self.allow_disk_offload,
                self.cache_dir,
                self.persistent_cache_root,
                self.download_on_startup,
                self.local_files_only,
                self.gpu_memory_limit,
                self.gpu_memory_utilization,
                self.kv_cache_vram_reserve,
                self.cpu_memory_limit,
                self.offload_dir,
            )
            self._assert_persistent_cache()
            self._log_cuda_state()
            self._log_cache_state("before_load")
            self._assert_cuda_requirement(resolved_device)

            try:
                self._configure_transformers_logging()
                self._snapshot_path = self._ensure_snapshot_downloaded()
                load_local_files_only = self.local_files_only or self._snapshot_path is not None
                from transformers import AutoModelForCausalLM, AutoTokenizer

                tokenizer_started = time.perf_counter()
                logger.info(
                    "Tokenizer load started model=%s cache_dir=%s local_files_only=%s snapshot_path=%s",
                    self.model_name_or_path,
                    self.cache_dir,
                    load_local_files_only,
                    self._snapshot_path,
                )
                with self._load_heartbeat("tokenizer_from_pretrained"):
                    self._tokenizer = AutoTokenizer.from_pretrained(
                        self.model_name_or_path,
                        cache_dir=self.cache_dir,
                        local_files_only=load_local_files_only,
                    )
                tokenizer_elapsed_ms = int((time.perf_counter() - tokenizer_started) * 1000)
                logger.info(
                    "Tokenizer load completed model=%s elapsed_ms=%s vocab_size=%s pad_token_id=%s eos_token_id=%s",
                    self.model_name_or_path,
                    tokenizer_elapsed_ms,
                    getattr(self._tokenizer, "vocab_size", None),
                    getattr(self._tokenizer, "pad_token_id", None),
                    getattr(self._tokenizer, "eos_token_id", None),
                )

                move_after_load = self._load_model_with_quantization_strategy(
                    AutoModelForCausalLM,
                    resolved_device,
                    load_local_files_only,
                )

                if move_after_load:
                    logger.info("Moving model to resolved_device=%s", resolved_device)
                    self._model.to(resolved_device)
                self._model.eval()
                placement = self._device_placement_status()
                self._last_placement_status = placement
                logger.info("Model placement summary model=%s placement=%s", self.model_name_or_path, placement)
                self._enforce_cuda_placement(placement)
                self._load_elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "Transformers model loaded model=%s elapsed_ms=%s cuda_memory=%s",
                    self.model_name_or_path,
                    self._load_elapsed_ms,
                    self._cuda_memory_status(),
                )
                self._log_cache_state("after_load")
            except Exception:
                logger.exception("Transformers model load failed model=%s status=%s", self.model_name_or_path, self.status())
                self._log_cache_state("after_failed_load")
                raise

    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False) -> str:
        self._load()
        assert self._tokenizer is not None
        assert self._model is not None
        with self._generate_lock:
            started = time.perf_counter()
            input_device = self._generation_input_device()
            prompt_text_input = prompt
            if json_mode:
                prompt_text_input = f"{prompt.rstrip()}\n\nRespond with valid JSON only."
            logger.debug(
                (
                    "Model generation started prompt_chars=%s requested_max_new_tokens=%s "
                    "configured_max_new_tokens=%s input_device=%s json_mode=%s cuda_memory=%s"
                ),
                len(prompt_text_input),
                max_new_tokens,
                self.max_new_tokens,
                input_device,
                json_mode,
                self._cuda_memory_status(),
            )
            messages = [{"role": "user", "content": prompt_text_input}]
            if hasattr(self._tokenizer, "apply_chat_template"):
                prompt_text = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                prompt_text = prompt_text_input
            encoded = self._tokenizer(prompt_text, return_tensors="pt")
            encoded = encoded.to(input_device)
            with torch.inference_mode():
                output = self._model.generate(
                    **encoded,
                    max_new_tokens=min(max_new_tokens, self.max_new_tokens),
                    temperature=self.temperature,
                    do_sample=self.temperature > 0,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            generated = output[0][encoded["input_ids"].shape[-1] :]
            decoded = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "Model generation completed output_chars=%s elapsed_ms=%s input_device=%s cuda_memory=%s",
                len(decoded),
                elapsed_ms,
                input_device,
                self._cuda_memory_status(),
            )
            return decoded

    def _configure_transformers_logging(self) -> None:
        try:
            from transformers.utils import logging as transformers_logging

            if logger.isEnabledFor(logging.DEBUG):
                transformers_logging.set_verbosity_debug()
            else:
                transformers_logging.set_verbosity_info()
            transformers_logging.enable_propagation()
        except Exception:
            logger.debug("Unable to configure Transformers library logging", exc_info=True)

    @contextmanager
    def _load_heartbeat(self, phase: str) -> Iterator[None]:
        stop_event = threading.Event()
        started = time.perf_counter()

        def emit() -> None:
            while not stop_event.wait(self.load_log_interval_seconds):
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "Model load still running phase=%s elapsed_ms=%s cuda_memory=%s cache=%s",
                    phase,
                    elapsed_ms,
                    self._cuda_memory_status(),
                    self._cache_brief_status(),
                )
                if logger.isEnabledFor(logging.DEBUG):
                    self._log_cache_state(f"during_{phase}")

        thread = threading.Thread(target=emit, name=f"model-load-{phase}", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop_event.set()
            thread.join(timeout=1)

    def _load_model_with_quantization_strategy(
        self,
        model_loader: Any,
        resolved_device: str,
        load_local_files_only: bool,
    ) -> bool:
        last_error: Exception | None = None
        strategies = self._quantization_strategies()
        self._quantization_attempts = []
        for index, strategy in enumerate(strategies, start=1):
            model_started = time.perf_counter()
            load_kwargs, move_after_load = self._build_load_kwargs(resolved_device, strategy)
            self._load_kwargs_summary = self._summarize_load_kwargs(load_kwargs)
            logger.info(
                "Model from_pretrained started model=%s quantization=%s attempt=%s/%s load_options=%s",
                self.model_name_or_path,
                strategy,
                index,
                len(strategies),
                self._load_kwargs_summary,
            )
            try:
                with self._load_heartbeat(f"model_from_pretrained_{strategy}"):
                    self._model = model_loader.from_pretrained(
                        self.model_name_or_path,
                        cache_dir=self.cache_dir,
                        local_files_only=load_local_files_only,
                        **load_kwargs,
                    )
                model_elapsed_ms = int((time.perf_counter() - model_started) * 1000)
                self._active_quantization = strategy
                self._quantization_attempts.append(
                    {
                        "quantization": strategy,
                        "status": "loaded",
                        "elapsed_ms": model_elapsed_ms,
                        "load_options": self._load_kwargs_summary,
                    }
                )
                logger.info(
                    "Model from_pretrained completed model=%s quantization=%s elapsed_ms=%s",
                    self.model_name_or_path,
                    strategy,
                    model_elapsed_ms,
                )
                return move_after_load
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - model_started) * 1000)
                last_error = exc
                self._model = None
                self._quantization_attempts.append(
                    {
                        "quantization": strategy,
                        "status": "failed",
                        "elapsed_ms": elapsed_ms,
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "load_options": self._load_kwargs_summary,
                    }
                )
                if index < len(strategies):
                    logger.exception(
                        "Model load failed for quantization=%s; trying next quantization strategy",
                        strategy,
                    )
                else:
                    logger.exception("Model load failed for final quantization=%s", strategy)
        assert last_error is not None
        raise last_error

    def _ensure_snapshot_downloaded(self) -> str | None:
        if self._is_local_model_path():
            snapshot_path = str(Path(self.model_name_or_path))
            logger.info("Model path is local; skipping Hugging Face snapshot download path=%s", snapshot_path)
            return snapshot_path
        if not self.download_on_startup and not self.local_files_only:
            logger.info(
                "Hugging Face snapshot preflight skipped model=%s download_on_startup=%s local_files_only=%s",
                self.model_name_or_path,
                self.download_on_startup,
                self.local_files_only,
            )
            return None

        from huggingface_hub import snapshot_download

        started = time.perf_counter()
        logger.info(
            (
                "Hugging Face snapshot preflight started model=%s cache_dir=%s local_files_only=%s "
                "download_on_startup=%s"
            ),
            self.model_name_or_path,
            self.cache_dir,
            self.local_files_only,
            self.download_on_startup,
        )
        with self._load_heartbeat("snapshot_download"):
            snapshot_path = snapshot_download(
                repo_id=self.model_name_or_path,
                cache_dir=self.cache_dir,
                local_files_only=self.local_files_only,
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Hugging Face snapshot preflight completed model=%s snapshot_path=%s elapsed_ms=%s cache=%s",
            self.model_name_or_path,
            snapshot_path,
            elapsed_ms,
            self._cache_brief_status(),
        )
        return snapshot_path

    def _assert_persistent_cache(self) -> None:
        if self.cache_dir:
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        if self.persistent_cache_root:
            Path(self.persistent_cache_root).mkdir(parents=True, exist_ok=True)

        mount_status = self._cache_mount_status()
        logger.info(
            "Persistent model cache check cache_dir=%s persistent_root=%s require=%s mount=%s env=%s",
            self.cache_dir,
            self.persistent_cache_root,
            self.require_persistent_cache,
            mount_status,
            self._cache_environment_status(),
        )
        if not self.require_persistent_cache:
            return
        if not self.cache_dir:
            raise RuntimeError("MODEL_REQUIRE_PERSISTENT_CACHE=true but MODEL_CACHE_DIR is empty.")
        if self.persistent_cache_root and not self._path_is_under(self.cache_dir, self.persistent_cache_root):
            raise RuntimeError(
                "MODEL_REQUIRE_PERSISTENT_CACHE=true but MODEL_CACHE_DIR is outside the persistent cache root: "
                f"cache_dir={self.cache_dir!r} persistent_root={self.persistent_cache_root!r}"
            )
        if mount_status.get("mountinfo_available") and self.persistent_cache_root:
            if not mount_status.get("persistent_root_is_mount"):
                raise RuntimeError(
                    "MODEL_REQUIRE_PERSISTENT_CACHE=true but the persistent cache root is not a mounted volume "
                    f"inside the container: persistent_root={self.persistent_cache_root!r} mount={mount_status!r}"
                )

    def _cache_mount_status(self) -> dict[str, Any]:
        cache_dir = self.cache_dir or ""
        persistent_root = self.persistent_cache_root or ""
        mounts = self._read_mountinfo()
        best_cache_mount = self._best_mount_for_path(cache_dir, mounts) if cache_dir else None
        persistent_root_path = self._normalize_posix_path(persistent_root) if persistent_root else None
        persistent_root_is_mount = False
        if persistent_root_path:
            persistent_root_is_mount = any(
                mount.get("mount_point") == persistent_root_path
                for mount in mounts
            )
        return {
            "cache_dir": cache_dir,
            "persistent_root": persistent_root,
            "mountinfo_available": Path("/proc/self/mountinfo").exists(),
            "persistent_root_is_mount": persistent_root_is_mount,
            "cache_mount": best_cache_mount,
        }

    def _read_mountinfo(self) -> list[dict[str, str]]:
        path = Path("/proc/self/mountinfo")
        if not path.exists():
            return []
        mounts: list[dict[str, str]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                before, _, after = line.partition(" - ")
                before_fields = before.split()
                after_fields = after.split()
                if len(before_fields) < 5 or len(after_fields) < 2:
                    continue
                mounts.append(
                    {
                        "mount_point": self._decode_mountinfo_path(before_fields[4]),
                        "fs_type": after_fields[0],
                        "source": self._decode_mountinfo_path(after_fields[1]),
                    }
                )
        except OSError:
            logger.debug("Unable to read /proc/self/mountinfo", exc_info=True)
        return mounts

    def _best_mount_for_path(self, path: str, mounts: list[dict[str, str]]) -> dict[str, str] | None:
        target = self._normalize_posix_path(path)
        matches = [
            mount
            for mount in mounts
            if self._posix_path_is_under(target, mount.get("mount_point", ""))
        ]
        if not matches:
            return None
        return max(matches, key=lambda mount: len(mount.get("mount_point", "")))

    def _cache_environment_status(self) -> dict[str, str | None]:
        keys = ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE", "SENTENCE_TRANSFORMERS_HOME")
        return {key: os.environ.get(key) for key in keys}

    def _is_local_model_path(self) -> bool:
        try:
            return Path(self.model_name_or_path).exists()
        except OSError:
            return False

    def _path_is_under(self, child: str, parent: str) -> bool:
        return self._posix_path_is_under(
            self._normalize_posix_path(child),
            self._normalize_posix_path(parent),
        )

    def _posix_path_is_under(self, child: str, parent: str) -> bool:
        if not child or not parent:
            return False
        child_path = PurePosixPath(child)
        parent_path = PurePosixPath(parent)
        return child_path == parent_path or parent_path in child_path.parents

    def _normalize_posix_path(self, path: str) -> str:
        return str(PurePosixPath(path.replace("\\", "/")))

    def _decode_mountinfo_path(self, path: str) -> str:
        return (
            path.replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )

    def _quantization_strategies(self) -> list[str]:
        requested = self._normalize_quantization(self.quantization)
        fallback = self._normalize_quantization(self.quantization_fallback)
        if requested == "legacy":
            requested = "4bit" if self.load_in_4bit else "none"
        if requested == "auto":
            candidates = ["4bit", "8bit"]
        else:
            candidates = [requested]
        if requested != "none" and fallback and fallback not in {"auto", "legacy"} and fallback not in candidates:
            candidates.append(fallback)
        if "none" in candidates and len(candidates) > 1:
            candidates = [candidate for candidate in candidates if candidate != "none"] + ["none"]
        logger.info("Quantization strategy order=%s", candidates)
        return candidates

    def _normalize_quantization(self, value: str | None) -> str:
        text = (value or "").strip().lower().replace("_", "-")
        aliases = {
            "": "legacy",
            "true": "4bit",
            "false": "none",
            "4": "4bit",
            "int4": "4bit",
            "bnb-4bit": "4bit",
            "load-in-4bit": "4bit",
            "8": "8bit",
            "int8": "8bit",
            "bnb-8bit": "8bit",
            "load-in-8bit": "8bit",
            "fp16": "none",
            "bf16": "none",
            "float16": "none",
            "float32": "none",
            "fp32": "none",
            "no": "none",
            "off": "none",
        }
        normalized = aliases.get(text, text)
        allowed = {"auto", "4bit", "8bit", "none", "legacy"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported MODEL_QUANTIZATION value: {value!r}. Use auto, 4bit, 8bit, or none.")
        return normalized

    def _build_load_kwargs(self, resolved_device: str, quantization: str) -> tuple[dict[str, Any], bool]:
        load_kwargs: dict[str, Any] = {
            "torch_dtype": "auto",
            "low_cpu_mem_usage": True,
        }
        move_after_load = False

        if self.device == "auto":
            if self.require_cuda and not self.allow_cpu_offload:
                device_index = self._cuda_device_index("cuda")
                load_kwargs["device_map"] = {"": device_index}
                logger.info(
                    "CUDA-only model placement selected device_map=%s; CPU and disk offload are disabled",
                    load_kwargs["device_map"],
                )
            else:
                load_kwargs["device_map"] = "auto"
                max_memory: dict[int | str, str] = {}
                memory_plan = self._memory_plan_status()
                logger.info("Model placement memory plan=%s", memory_plan)
                effective_gpu_limit = memory_plan.get("effective_gpu_memory_limit")
                if torch.cuda.is_available() and effective_gpu_limit:
                    max_memory[self._cuda_device_index("cuda")] = int(effective_gpu_limit)
                if self.allow_cpu_offload and self.cpu_memory_limit:
                    max_memory["cpu"] = self.cpu_memory_limit
                if max_memory:
                    load_kwargs["max_memory"] = max_memory
                if self.allow_cpu_offload and self.allow_disk_offload and self.offload_dir:
                    Path(self.offload_dir).mkdir(parents=True, exist_ok=True)
                    load_kwargs["offload_folder"] = self.offload_dir
                    logger.warning(
                        "Model disk offload is enabled; this can be much slower than CPU RAM offload offload_dir=%s",
                        self.offload_dir,
                    )
                elif self.offload_dir:
                    logger.info(
                        "Model disk offload disabled; ignoring offload_dir=%s allow_cpu_offload=%s allow_disk_offload=%s",
                        self.offload_dir,
                        self.allow_cpu_offload,
                        self.allow_disk_offload,
                    )
        else:
            if self.load_in_4bit and resolved_device.startswith("cuda"):
                load_kwargs["device_map"] = {"": self._cuda_device_index(resolved_device)}
            else:
                move_after_load = True

        if quantization in {"4bit", "8bit"}:
            if not torch.cuda.is_available():
                raise RuntimeError(f"MODEL_QUANTIZATION={quantization} requires CUDA to be available inside the backend container.")
            if not (self.device == "auto" or resolved_device.startswith("cuda")):
                raise RuntimeError(f"MODEL_QUANTIZATION={quantization} requires MODEL_DEVICE=auto or a CUDA device.")
            from transformers import BitsAndBytesConfig

            if quantization == "4bit":
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
            else:
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_enable_fp32_cpu_offload=self.allow_cpu_offload,
                )
        elif quantization != "none":
            raise ValueError(f"Unsupported quantization strategy: {quantization}")

        return load_kwargs, move_after_load

    def _summarize_load_kwargs(self, load_kwargs: dict[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for key, value in load_kwargs.items():
            if key == "quantization_config":
                if getattr(value, "load_in_4bit", False):
                    summary[key] = "bitsandbytes_4bit_nf4_float16_double_quant"
                elif getattr(value, "load_in_8bit", False):
                    summary[key] = {
                        "mode": "bitsandbytes_8bit",
                        "fp32_cpu_offload": getattr(value, "llm_int8_enable_fp32_cpu_offload", None),
                    }
                else:
                    summary[key] = value.__class__.__name__
            elif key == "max_memory" and isinstance(value, dict):
                summary[key] = {
                    device: self._format_bytes(limit) if isinstance(limit, int) else limit
                    for device, limit in value.items()
                }
            else:
                summary[key] = value
        return summary

    def _assert_cuda_requirement(self, resolved_device: str) -> None:
        if not self.require_cuda:
            return
        if not torch.cuda.is_available():
            raise RuntimeError(
                "MODEL_REQUIRE_CUDA=true but CUDA is not available inside the backend container. "
                "Backend startup is stopped to prevent CPU inference fallback."
            )
        if not resolved_device.startswith("cuda"):
            raise RuntimeError(
                f"MODEL_REQUIRE_CUDA=true but the resolved model device is {resolved_device!r}. "
                "Set MODEL_DEVICE=auto or a CUDA device."
            )

    def _enforce_cuda_placement(self, placement: dict[str, Any]) -> None:
        if not self.require_cuda:
            return
        device_map = placement.get("hf_device_map") or {}
        disk_map_entries = {
            name: value
            for name, value in device_map.items()
            if self._device_map_value_is_disk(value)
        }
        cpu_map_entries = {
            name: value
            for name, value in device_map.items()
            if self._device_map_value_is_cpu(value)
        }
        if disk_map_entries and not self.allow_disk_offload:
            raise RuntimeError(
                "MODEL_ALLOW_DISK_OFFLOAD=false but the loaded device map contains disk entries: "
                f"{disk_map_entries}"
            )
        if cpu_map_entries and not self.allow_cpu_offload:
            raise RuntimeError(
                "MODEL_ALLOW_CPU_OFFLOAD=false but the loaded device map contains CPU entries: "
                f"{cpu_map_entries}"
            )
        if not self._placement_uses_cuda(placement):
            raise RuntimeError(
                "MODEL_REQUIRE_CUDA=true but no model weights appear to be placed on CUDA. "
                f"placement={placement}"
            )
        if placement.get("parameter_non_cuda_count", 0) and not self.allow_cpu_offload:
            raise RuntimeError(
                "MODEL_REQUIRE_CUDA=true but some model parameters are not on CUDA: "
                f"{placement.get('parameter_non_cuda_examples')}"
            )
        if placement.get("parameter_non_cuda_count", 0) and self.allow_cpu_offload:
            logger.info(
                "Model CPU offload active parameter_non_cuda_count=%s examples=%s",
                placement.get("parameter_non_cuda_count"),
                placement.get("parameter_non_cuda_examples"),
            )
        if placement.get("buffer_non_cuda_count", 0):
            logger.warning(
                "Model has non-CUDA buffers while MODEL_REQUIRE_CUDA=true buffer_count=%s examples=%s",
                placement.get("buffer_non_cuda_count"),
                placement.get("buffer_non_cuda_examples"),
            )

    def _generation_input_device(self) -> torch.device:
        assert self._model is not None
        device_map = getattr(self._model, "hf_device_map", None)
        if device_map:
            for value in device_map.values():
                device = self._device_from_map_value(value)
                if device is not None and device.type == "cuda":
                    return device
            if self.require_cuda:
                raise RuntimeError(
                    f"MODEL_REQUIRE_CUDA=true but generation device map has no CUDA entries: {device_map}"
                )
        if self.require_cuda:
            for parameter in self._model.parameters():
                if parameter.device.type == "cuda":
                    return parameter.device
            raise RuntimeError("MODEL_REQUIRE_CUDA=true but no CUDA model parameter is available for generation input.")
        for parameter in self._model.parameters():
            if parameter.device.type != "meta":
                return parameter.device
        fallback = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        if self.require_cuda and fallback.type != "cuda":
            raise RuntimeError("MODEL_REQUIRE_CUDA=true but no CUDA generation input device is available.")
        return fallback

    def _device_from_map_value(self, value: Any) -> torch.device | None:
        if isinstance(value, int):
            return torch.device(f"cuda:{value}")
        text = str(value).lower()
        if text.startswith("cuda"):
            return torch.device(text)
        return None

    def _device_map_value_is_cpu(self, value: Any) -> bool:
        text = str(value).lower()
        return "cpu" in text

    def _device_map_value_is_disk(self, value: Any) -> bool:
        text = str(value).lower()
        return "disk" in text

    def _placement_uses_cuda(self, placement: dict[str, Any]) -> bool:
        device_map = placement.get("hf_device_map") or {}
        if any(str(value).lower().startswith("cuda") or isinstance(value, int) for value in device_map.values()):
            return True
        parameter_devices = placement.get("parameter_devices") or {}
        return any(str(device).startswith("cuda") for device in parameter_devices)

    def _cuda_device_index(self, device: str) -> int:
        if ":" in device:
            try:
                return int(device.split(":", 1)[1])
            except ValueError:
                logger.warning("Unable to parse CUDA device index from device=%s; using current device", device)
        if torch.cuda.is_available():
            return torch.cuda.current_device()
        return 0

    def _device_placement_status(self) -> dict[str, Any]:
        if self._model is None:
            return {}
        parameter_devices: dict[str, int] = {}
        parameter_non_cuda_examples: list[str] = []
        buffer_devices: dict[str, int] = {}
        buffer_non_cuda_examples: list[str] = []

        for name, parameter in self._model.named_parameters():
            device = str(parameter.device)
            parameter_devices[device] = parameter_devices.get(device, 0) + parameter.numel()
            if parameter.device.type != "cuda" and len(parameter_non_cuda_examples) < 10:
                parameter_non_cuda_examples.append(f"{name}:{device}")

        for name, buffer in self._model.named_buffers():
            device = str(buffer.device)
            buffer_devices[device] = buffer_devices.get(device, 0) + buffer.numel()
            if buffer.device.type != "cuda" and len(buffer_non_cuda_examples) < 10:
                buffer_non_cuda_examples.append(f"{name}:{device}")

        hf_device_map = getattr(self._model, "hf_device_map", None)
        return {
            "hf_device_map": hf_device_map,
            "parameter_devices": parameter_devices,
            "parameter_non_cuda_count": sum(
                count for device, count in parameter_devices.items() if not device.startswith("cuda")
            ),
            "parameter_non_cuda_examples": parameter_non_cuda_examples,
            "buffer_devices": buffer_devices,
            "buffer_non_cuda_count": sum(
                count for device, count in buffer_devices.items() if not device.startswith("cuda")
            ),
            "buffer_non_cuda_examples": buffer_non_cuda_examples,
        }

    def _cuda_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "available": False,
            "device_count": 0,
            "devices": [],
            "memory": self._cuda_memory_status(),
        }
        try:
            available = torch.cuda.is_available()
            status["available"] = available
            status["device_count"] = torch.cuda.device_count() if available else 0
            devices = []
            for index in range(int(status["device_count"])):
                props = torch.cuda.get_device_properties(index)
                free_bytes = None
                total_bytes = props.total_memory
                try:
                    with torch.cuda.device(index):
                        free_bytes, total_bytes = torch.cuda.mem_get_info()
                except Exception:
                    logger.debug("Unable to inspect CUDA memory for device=%s", index, exc_info=True)
                devices.append(
                    {
                        "index": index,
                        "name": props.name,
                        "capability": f"{props.major}.{props.minor}",
                        "total_memory_bytes": total_bytes,
                        "total_memory_human": self._format_bytes(total_bytes),
                        "free_memory_bytes": free_bytes,
                        "free_memory_human": self._format_bytes(free_bytes) if free_bytes is not None else None,
                    }
                )
            status["devices"] = devices
        except Exception as exc:
            status["error"] = f"{exc.__class__.__name__}: {exc}"
        return status

    def _cuda_memory_status(self) -> dict[str, Any]:
        if not torch.cuda.is_available():
            return {"available": False}
        try:
            index = torch.cuda.current_device()
            free_bytes, total_bytes = torch.cuda.mem_get_info(index)
            return {
                "available": True,
                "device_index": index,
                "allocated_bytes": torch.cuda.memory_allocated(index),
                "reserved_bytes": torch.cuda.memory_reserved(index),
                "free_bytes": free_bytes,
                "total_bytes": total_bytes,
                "allocated_human": self._format_bytes(torch.cuda.memory_allocated(index)),
                "reserved_human": self._format_bytes(torch.cuda.memory_reserved(index)),
                "free_human": self._format_bytes(free_bytes),
                "total_human": self._format_bytes(total_bytes),
            }
        except Exception as exc:
            return {"available": True, "error": f"{exc.__class__.__name__}: {exc}"}

    def _memory_plan_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "allow_cpu_offload": self.allow_cpu_offload,
            "allow_disk_offload": self.allow_disk_offload,
            "configured_gpu_memory_limit": self.gpu_memory_limit,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "kv_cache_vram_reserve": self.kv_cache_vram_reserve,
            "cpu_memory_limit": self.cpu_memory_limit,
            "effective_gpu_memory_limit": None,
            "effective_gpu_memory_limit_human": None,
        }
        if not torch.cuda.is_available():
            status["cuda_available"] = False
            return status
        try:
            index = torch.cuda.current_device()
            free_bytes, total_bytes = torch.cuda.mem_get_info(index)
            configured_gpu_bytes = self._parse_memory_limit_bytes(self.gpu_memory_limit)
            reserve_bytes = self._parse_memory_limit_bytes(self.kv_cache_vram_reserve) or 0
            utilization = self.gpu_memory_utilization
            utilization_bytes = None
            if utilization > 0:
                utilization_bytes = int(total_bytes * utilization)
            free_minus_reserve = max(0, free_bytes - reserve_bytes)
            candidates = [
                value
                for value in (configured_gpu_bytes, utilization_bytes, free_minus_reserve)
                if value is not None and value > 0
            ]
            effective_bytes = min(candidates) if candidates else None
            status.update(
                {
                    "cuda_available": True,
                    "device_index": index,
                    "total_vram_bytes": total_bytes,
                    "free_vram_bytes": free_bytes,
                    "total_vram_human": self._format_bytes(total_bytes),
                    "free_vram_human": self._format_bytes(free_bytes),
                    "configured_gpu_memory_limit_bytes": configured_gpu_bytes,
                    "configured_gpu_memory_limit_human": self._format_bytes(configured_gpu_bytes)
                    if configured_gpu_bytes is not None
                    else None,
                    "utilization_gpu_memory_limit_bytes": utilization_bytes,
                    "utilization_gpu_memory_limit_human": self._format_bytes(utilization_bytes)
                    if utilization_bytes is not None
                    else None,
                    "kv_cache_vram_reserve_bytes": reserve_bytes,
                    "kv_cache_vram_reserve_human": self._format_bytes(reserve_bytes),
                    "free_after_reserve_bytes": free_minus_reserve,
                    "free_after_reserve_human": self._format_bytes(free_minus_reserve),
                    "effective_gpu_memory_limit": effective_bytes,
                    "effective_gpu_memory_limit_human": self._format_bytes(effective_bytes)
                    if effective_bytes is not None
                    else None,
                }
            )
            return status
        except Exception as exc:
            status["error"] = f"{exc.__class__.__name__}: {exc}"
            return status

    def _parse_memory_limit_bytes(self, value: str | None) -> int | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        units = {
            "b": 1,
            "kib": 1024,
            "kb": 1000,
            "mib": 1024**2,
            "mb": 1000**2,
            "gib": 1024**3,
            "gb": 1000**3,
            "tib": 1024**4,
            "tb": 1000**4,
        }
        number = ""
        unit = ""
        for character in text:
            if character.isdigit() or character == ".":
                number += character
            elif not character.isspace():
                unit += character.lower()
        if not number:
            return None
        multiplier = units.get(unit or "b")
        if multiplier is None:
            raise ValueError(f"Unsupported memory limit unit in value={value!r}")
        return int(float(number) * multiplier)

    def _log_cuda_state(self) -> None:
        status = self._cuda_status()
        logger.info(
            "CUDA state torch_version=%s torch_cuda_version=%s available=%s device_count=%s require_cuda=%s",
            status.get("torch_version"),
            status.get("torch_cuda_version"),
            status.get("available"),
            status.get("device_count"),
            self.require_cuda,
        )
        for device in status.get("devices", []):
            logger.info(
                "CUDA device index=%s name=%s capability=%s total_memory=%s free_memory=%s",
                device.get("index"),
                device.get("name"),
                device.get("capability"),
                device.get("total_memory_human"),
                device.get("free_memory_human"),
            )

    def _log_cache_state(self, phase: str) -> None:
        for summary in self._cache_status():
            logger.info(
                (
                    "Model cache %s path=%s exists=%s files=%s dirs=%s size=%s "
                    "model_files=%s model_size=%s incomplete_files=%s truncated=%s"
                ),
                phase,
                summary.get("path"),
                summary.get("exists"),
                summary.get("file_count"),
                summary.get("dir_count"),
                summary.get("total_size_human"),
                summary.get("model_file_count"),
                summary.get("model_file_size_human"),
                summary.get("incomplete_file_count"),
                summary.get("truncated"),
            )
            if summary.get("incomplete_examples"):
                logger.warning(
                    "Model cache %s has incomplete artifacts path=%s examples=%s",
                    phase,
                    summary.get("path"),
                    summary.get("incomplete_examples"),
                )

    def _cache_status(self) -> list[dict[str, Any]]:
        paths: list[Path] = []
        model_path = Path(self.model_name_or_path)
        if model_path.exists():
            paths.append(model_path)
        if self.cache_dir:
            root = Path(self.cache_dir)
            model_key = f"models--{self.model_name_or_path.replace('/', '--')}"
            paths.extend([root / model_key, root / "hub" / model_key, root])

        seen: set[str] = set()
        summaries = []
        for path in paths:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            summaries.append(self._summarize_cache_path(path))
        return summaries

    def _cache_brief_status(self) -> list[dict[str, Any]]:
        return [
            {
                "path": summary.get("path"),
                "exists": summary.get("exists"),
                "files": summary.get("file_count"),
                "size": summary.get("total_size_human"),
                "model_files": summary.get("model_file_count"),
                "model_size": summary.get("model_file_size_human"),
                "incomplete_files": summary.get("incomplete_file_count"),
                "truncated": summary.get("truncated"),
            }
            for summary in self._cache_status()
        ]

    def _summarize_cache_path(self, path: Path, max_entries: int = 5000) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
            "file_count": 0,
            "dir_count": 0,
            "total_size_bytes": 0,
            "total_size_human": "0 B",
            "model_file_count": 0,
            "model_file_size_bytes": 0,
            "model_file_size_human": "0 B",
            "incomplete_file_count": 0,
            "incomplete_examples": [],
            "truncated": False,
        }
        if not path.exists():
            return summary
        try:
            if path.is_file():
                size = path.stat().st_size
                summary.update(
                    {
                        "file_count": 1,
                        "total_size_bytes": size,
                        "total_size_human": self._format_bytes(size),
                        "model_file_count": 1 if self._is_model_file(path) else 0,
                        "model_file_size_bytes": size if self._is_model_file(path) else 0,
                        "model_file_size_human": self._format_bytes(size) if self._is_model_file(path) else "0 B",
                    }
                )
                return summary

            scanned = 0
            incomplete_examples: list[str] = []
            for child in path.rglob("*"):
                scanned += 1
                if scanned > max_entries:
                    summary["truncated"] = True
                    break
                try:
                    if child.is_dir():
                        summary["dir_count"] += 1
                        continue
                    size = child.stat().st_size
                    summary["file_count"] += 1
                    summary["total_size_bytes"] += size
                    if self._is_model_file(child):
                        summary["model_file_count"] += 1
                        summary["model_file_size_bytes"] += size
                    if child.name.endswith(".incomplete") or child.name.endswith(".lock"):
                        summary["incomplete_file_count"] += 1
                        if len(incomplete_examples) < 10:
                            incomplete_examples.append(str(child.relative_to(path)))
                except OSError:
                    logger.debug("Unable to inspect model cache entry path=%s", child, exc_info=True)
            summary["incomplete_examples"] = incomplete_examples
            summary["total_size_human"] = self._format_bytes(int(summary["total_size_bytes"]))
            summary["model_file_size_human"] = self._format_bytes(int(summary["model_file_size_bytes"]))
            return summary
        except OSError as exc:
            summary["error"] = f"{exc.__class__.__name__}: {exc}"
            return summary

    def _is_model_file(self, path: Path) -> bool:
        return path.suffix in {".safetensors", ".bin", ".pt", ".pth", ".gguf"}

    def _format_bytes(self, value: int | None) -> str:
        if value is None:
            return "unknown"
        amount = float(value)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if amount < 1024 or unit == "TiB":
                return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
            amount /= 1024
        return f"{amount:.1f} TiB"
