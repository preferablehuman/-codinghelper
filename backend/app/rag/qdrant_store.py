import logging
from uuid import uuid4

from app.config import get_settings


logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def upsert_chunks(self, vectors: list[list[float]], payloads: list[dict[str, object]]) -> list[str]:
        if not vectors:
            logger.info("Qdrant upsert skipped because vector list is empty")
            return []
        point_ids = [str(uuid4()) for _ in vectors]
        vector_size = len(vectors[0])
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams

            client = QdrantClient(url=self.settings.qdrant_url)
            self._ensure_collection(client, vector_size, Distance, VectorParams)
            client.upsert(
                collection_name=self.settings.qdrant_collection,
                points=[
                    PointStruct(id=point_id, vector=vector, payload=payload)
                    for point_id, vector, payload in zip(point_ids, vectors, payloads, strict=True)
                ],
            )
            logger.info("Qdrant upsert complete collection=%s count=%s", self.settings.qdrant_collection, len(vectors))
        except Exception:
            # The database remains the source of truth. Qdrant failure should not erase job progress.
            logger.exception("Qdrant upsert failed collection=%s count=%s", self.settings.qdrant_collection, len(vectors))
            return ["" for _ in vectors]
        return point_ids

    def search_chunks(self, query_vector: list[float], limit: int = 5, score_threshold: float = 0.65) -> list[dict[str, object]]:
        if not query_vector:
            return []
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=self.settings.qdrant_url)
            if not client.collection_exists(self.settings.qdrant_collection):
                logger.info("Qdrant search skipped because collection does not exist collection=%s", self.settings.qdrant_collection)
                return []
            try:
                response = client.search(
                    collection_name=self.settings.qdrant_collection,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
            except AttributeError:
                query_response = client.query_points(
                    collection_name=self.settings.qdrant_collection,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
                response = getattr(query_response, "points", [])
            results = [
                {
                    "id": str(getattr(point, "id", "")),
                    "score": float(getattr(point, "score", 0.0) or 0.0),
                    "payload": getattr(point, "payload", {}) or {},
                }
                for point in response
            ]
            logger.info("Qdrant search complete collection=%s count=%s", self.settings.qdrant_collection, len(results))
            return results
        except Exception:
            logger.exception("Qdrant search failed collection=%s", self.settings.qdrant_collection)
            return []

    def _ensure_collection(self, client, vector_size: int, distance_type, vector_params_type) -> None:
        collection = self.settings.qdrant_collection
        if not client.collection_exists(collection):
            self._create_collection(client, vector_size, distance_type, vector_params_type)
            return

        existing_size = self._collection_vector_size(client.get_collection(collection))
        if existing_size == vector_size:
            logger.debug("Qdrant collection vector size verified collection=%s vector_size=%s", collection, vector_size)
            return
        if existing_size is None:
            logger.warning(
                "Could not determine Qdrant collection vector size; leaving collection unchanged collection=%s expected_vector_size=%s",
                collection,
                vector_size,
            )
            return

        logger.warning(
            (
                "Recreating Qdrant collection because embedding dimension changed collection=%s "
                "existing_vector_size=%s expected_vector_size=%s"
            ),
            collection,
            existing_size,
            vector_size,
        )
        client.delete_collection(collection_name=collection)
        self._create_collection(client, vector_size, distance_type, vector_params_type)

    def _create_collection(self, client, vector_size: int, distance_type, vector_params_type) -> None:
        collection = self.settings.qdrant_collection
        logger.info("Creating Qdrant collection collection=%s vector_size=%s", collection, vector_size)
        client.create_collection(
            collection_name=collection,
            vectors_config=vector_params_type(size=vector_size, distance=distance_type.COSINE),
        )

    def _collection_vector_size(self, collection_info) -> int | None:
        config = getattr(collection_info, "config", None)
        params = getattr(config, "params", None)
        vectors = getattr(params, "vectors", None)
        if vectors is None and isinstance(params, dict):
            vectors = params.get("vectors")
        return self._vector_size_from_config(vectors)

    def _vector_size_from_config(self, vectors) -> int | None:
        size = getattr(vectors, "size", None)
        if isinstance(size, int):
            return size
        if isinstance(vectors, dict):
            if isinstance(vectors.get("size"), int):
                return vectors["size"]
            for value in vectors.values():
                nested_size = self._vector_size_from_config(value)
                if nested_size is not None:
                    return nested_size
        return None
