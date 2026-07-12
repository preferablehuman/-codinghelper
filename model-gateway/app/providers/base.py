from abc import ABC, abstractmethod
from typing import Any


class ModelProvider(ABC):
    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        raise NotImplementedError
