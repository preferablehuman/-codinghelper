import html
import re
import httpx

from app.config import get_settings
from app.retrieval.adapters.base import ExternalProblemCandidate, RetrievalAdapter
from app.retrieval.compliance import get_policy


class StackExchangeAdapter(RetrievalAdapter):
    name = "stack_exchange"

    def discover(self, query: str, *, limit: int) -> list[ExternalProblemCandidate]:
        policy = get_policy(self.name)
        if not policy.allow_discovery:
            return []
        settings = get_settings()
        params = {"site": "stackoverflow", "intitle": query[:120], "pagesize": min(limit, 20), "order": "desc", "sort": "relevance", "filter": "withbody"}
        if settings.stack_exchange_key:
            params["key"] = settings.stack_exchange_key
        response = httpx.get("https://api.stackexchange.com/2.3/search/advanced", params=params, timeout=settings.external_fetch_timeout_seconds)
        response.raise_for_status()
        candidates: list[ExternalProblemCandidate] = []
        for item in response.json().get("items", [])[:limit]:
            question_id = str(item.get("question_id", ""))
            body = _plain_text(str(item.get("body", "")))[: policy.max_chars_to_store]
            candidates.append(ExternalProblemCandidate(
                title=html.unescape(str(item.get("title", "Stack Overflow question"))),
                url=str(item.get("link", "")), source_name=self.name, source_tier=2,
                external_problem_id=question_id or None, statement_text=body or None,
                tags=[str(tag) for tag in item.get("tags", [])],
                attribution=f"Stack Overflow question {question_id}; author {item.get('owner', {}).get('display_name', 'unknown')}",
                license_note="Stack Exchange content; retain source attribution and applicable CC license.",
                retrieval_method="stack_exchange_official_api", storage_capability="snippet",
            ))
        return candidates


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()
