import os
import resource


def prepare_process(memory_mb: int | None) -> None:
    if memory_mb is not None:
        memory_bytes = max(memory_mb, 64) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    os.setsid()


def limit_process(memory_mb: int) -> None:
    prepare_process(memory_mb)
