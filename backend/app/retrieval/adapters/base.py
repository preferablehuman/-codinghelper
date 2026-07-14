from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExternalProblemCandidate:
    title: str
    url: str
    source_name: str
    source_tier: int
    external_problem_id: str | None = None
    statement_text: str | None = None
    solution_text: str | None = None
    code_blocks: list[str] = field(default_factory=list)
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    attribution: str | None = None
    license_note: str | None = None
    retrieval_method: str = ""
    storage_capability: str = "metadata_only"
    rejection_reason: str | None = None


class RetrievalAdapter(ABC):
    name: str

    @abstractmethod
    def discover(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]: ...
