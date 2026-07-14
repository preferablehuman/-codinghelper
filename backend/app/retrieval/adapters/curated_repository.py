from app.retrieval.adapters.base import ExternalProblemCandidate, RetrievalAdapter
from app.retrieval.compliance import get_policy


class CuratedRepositoryAdapter(RetrievalAdapter):
    name = "curated_repository"
    ALLOWLIST = {"TheAlgorithms/Python", "TheAlgorithms/Java"}

    def discover(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]:
        if not get_policy("the_algorithms").allow_discovery:
            return []
        # No arbitrary GitHub search: this adapter exposes allowlisted repository roots
        # as related evidence until a licensed local index is configured.
        return [
            ExternalProblemCandidate(
                title=f"The Algorithms {language} repository",
                url=f"https://github.com/TheAlgorithms/{language}", source_name="the_algorithms", source_tier=1,
                tags=[query], attribution=f"TheAlgorithms/{language}", license_note="MIT; verify file provenance before code promotion.",
                retrieval_method="curated_allowlist", storage_capability="metadata_only",
            )
            for language in ("Python", "Java")
        ][:limit]
