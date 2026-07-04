import hashlib
import logging
import math
from functools import lru_cache
from pathlib import Path

VECTOR_SIZE = 384
logger = logging.getLogger(__name__)


def deterministic_embedding(text: str, size: int = VECTOR_SIZE) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for index in range(size):
        byte = digest[index % len(digest)]
        values.append((byte / 255.0) - 0.5)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


@lru_cache(maxsize=1)
def _load_sentence_transformer(model_name: str, cache_dir: str | None):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, cache_folder=cache_dir)


def embed_texts(
    texts: list[str],
    model_name: str | None = None,
    allow_remote_download: bool = True,
    cache_dir: str | None = None,
) -> list[list[float]]:
    if not texts:
        logger.info("Embedding skipped because text list is empty")
        return []
    can_load_model = bool(model_name and (allow_remote_download or Path(model_name).exists()))
    if can_load_model:
        try:
            logger.info("Embedding texts with sentence transformer model=%s count=%s", model_name, len(texts))
            model = _load_sentence_transformer(model_name, cache_dir)
            vectors = [list(vector) for vector in model.encode(texts, normalize_embeddings=True)]
            logger.info("Sentence transformer embedding complete count=%s vector_size=%s", len(vectors), len(vectors[0]) if vectors else 0)
            return vectors
        except Exception:
            logger.exception("Sentence transformer embedding failed; using deterministic fallback")
    logger.info("Embedding texts with deterministic fallback count=%s vector_size=%s", len(texts), VECTOR_SIZE)
    return [deterministic_embedding(text) for text in texts]
