from abc import ABC, abstractmethod
from typing import Any


class BaseModelRuntime(ABC):
    def load(self) -> None:
        raise NotImplementedError

    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int = 1024, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        raise NotImplementedError
