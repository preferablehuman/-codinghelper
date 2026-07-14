from __future__ import annotations

from abc import ABC, abstractmethod

from app.retrieval.adapters.base import ExternalProblemCandidate


class SearchProvider(ABC):
    """Extension point for a configured search API; result-page scraping is prohibited."""

    @abstractmethod
    def search(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]: ...


def configured_search_provider() -> SearchProvider | None:
    # Intentionally disabled until an explicit supported search API and key are configured.
    return None
