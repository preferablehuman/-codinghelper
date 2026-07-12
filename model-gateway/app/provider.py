from functools import lru_cache

from app.config import get_settings
from app.providers.base import ModelProvider
from app.providers.langchain import LangChainProvider


@lru_cache(maxsize=1)
def get_provider() -> ModelProvider:
    return LangChainProvider.from_settings(get_settings())
