from app.config import get_settings
from app.retrieval.adapters.base import RetrievalAdapter
from app.retrieval.adapters.codeforces import CodeforcesAdapter
from app.retrieval.adapters.curated_repository import CuratedRepositoryAdapter
from app.retrieval.adapters.stack_exchange import StackExchangeAdapter
from app.retrieval.adapters.user_url import UserURLAdapter


def enabled_adapters(user_urls: list[str] | None = None) -> list[RetrievalAdapter]:
    enabled = {item.strip() for item in get_settings().enabled_retrieval_adapters.split(",") if item.strip()}
    registry: dict[str, RetrievalAdapter] = {
        "stack_exchange": StackExchangeAdapter(), "codeforces": CodeforcesAdapter(),
        "curated_repository": CuratedRepositoryAdapter(), "user_url": UserURLAdapter(user_urls),
    }
    return [registry[name] for name in registry if name in enabled]
