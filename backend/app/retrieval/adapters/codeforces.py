import httpx

from app.config import get_settings
from app.retrieval.adapters.base import ExternalProblemCandidate, RetrievalAdapter
from app.retrieval.compliance import get_policy


class CodeforcesAdapter(RetrievalAdapter):
    name = "codeforces"

    def discover(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]:
        if not get_policy(self.name).allow_discovery:
            return []
        response = httpx.get("https://codeforces.com/api/problemset.problems", timeout=get_settings().external_fetch_timeout_seconds)
        response.raise_for_status()
        terms = set(query.casefold().split())
        scored = []
        for problem in response.json().get("result", {}).get("problems", []):
            title = str(problem.get("name", ""))
            score = len(terms & set(title.casefold().split()))
            if score:
                scored.append((score, problem))
        candidates = []
        for _, item in sorted(scored, key=lambda row: row[0], reverse=True)[:limit]:
            contest, index = item.get("contestId"), item.get("index")
            candidates.append(ExternalProblemCandidate(
                title=str(item.get("name", "Codeforces problem")),
                url=f"https://codeforces.com/problemset/problem/{contest}/{index}",
                source_name=self.name, source_tier=2, external_problem_id=f"{contest}-{index}",
                tags=[str(tag) for tag in item.get("tags", [])],
                attribution="Codeforces public problem metadata", license_note="Metadata only; statement, editorial, and submissions are not ingested.",
                retrieval_method="codeforces_official_api", storage_capability="metadata_only",
            ))
        return candidates
