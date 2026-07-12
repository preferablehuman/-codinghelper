import logging
from uuid import uuid4

from app.config import get_settings


logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def upsert_chunks(self, vectors: list[list[float]], payloads: list[dict[str, object]]) -> list[str]:
        return self._upsert(self.settings.qdrant_collection, vectors, payloads)

    def upsert_problem_variant(self, vector: list[float], payload: dict[str, object], point_id: str | None = None) -> str:
        ids = self._upsert(self.settings.qdrant_problem_collection, [vector], [payload], [point_id] if point_id else None)
        return ids[0] if ids else ""

    def search_problem_variants(self, query_vector: list[float], limit: int = 10, score_threshold: float = 0.0) -> list[dict[str, object]]:
        return self._search(self.settings.qdrant_problem_collection, query_vector, limit, score_threshold)

    def delete_problem_variant(self, point_id: str) -> None:
        self._delete_points(self.settings.qdrant_problem_collection, [point_id])

    def upsert_knowledge_chunks(self, vectors: list[list[float]], payloads: list[dict[str, object]]) -> list[str]:
        return self._upsert(self.settings.qdrant_knowledge_collection, vectors, payloads)

    def search_knowledge_chunks(self, query_vector: list[float], limit: int = 10, score_threshold: float = 0.0) -> list[dict[str, object]]:
        return self._search(self.settings.qdrant_knowledge_collection, query_vector, limit, score_threshold)

    def delete_knowledge_source(self, knowledge_source_id: str) -> None:
        self._delete_by_filter(self.settings.qdrant_knowledge_collection, "knowledge_source_id", knowledge_source_id)

    def delete_knowledge_chunk(self, point_id: str) -> None:
        self._delete_points(self.settings.qdrant_knowledge_collection, [point_id])

    def ensure_collections(self, vector_size: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        client = QdrantClient(url=self.settings.qdrant_url)
        for collection in (self.settings.qdrant_collection, self.settings.qdrant_problem_collection, self.settings.qdrant_knowledge_collection):
            self._ensure_named_collection(client, collection, vector_size, Distance, VectorParams)

    def _upsert(self, collection: str, vectors: list[list[float]], payloads: list[dict[str, object]], point_ids: list[str | None] | None = None) -> list[str]:
        if not vectors:
            logger.info("Qdrant upsert skipped because vector list is empty")
            return []
        resolved_ids = [point_id or str(uuid4()) for point_id in point_ids] if point_ids else [str(uuid4()) for _ in vectors]
        vector_size = len(vectors[0])
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams

            client = QdrantClient(url=self.settings.qdrant_url)
            self._ensure_named_collection(client, collection, vector_size, Distance, VectorParams)
            client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(id=point_id, vector=vector, payload=payload)
                    for point_id, vector, payload in zip(resolved_ids, vectors, payloads, strict=True)
                ],
            )
            logger.info("Qdrant upsert complete collection=%s count=%s", collection, len(vectors))
        except Exception:
            # The database remains the source of truth. Qdrant failure should not erase job progress.
            logger.exception("Qdrant upsert failed collection=%s count=%s", collection, len(vectors))
            return ["" for _ in vectors]
        return resolved_ids

    def search_chunks(self, query_vector: list[float], limit: int = 5, score_threshold: float = 0.65) -> list[dict[str, object]]:
        return self._search(self.settings.qdrant_collection, query_vector, limit, score_threshold)

    def _search(self, collection: str, query_vector: list[float], limit: int, score_threshold: float) -> list[dict[str, object]]:
        if not query_vector:
            return []
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=self.settings.qdrant_url)
            if not client.collection_exists(collection):
                logger.info("Qdrant search skipped because collection does not exist collection=%s", collection)
                return []
            try:
                response = client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
            except AttributeError:
                query_response = client.query_points(
                    collection_name=collection,
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
            logger.info("Qdrant search complete collection=%s count=%s", collection, len(results))
            return results
        except Exception:
            logger.exception("Qdrant search failed collection=%s", collection)
            return []

    def _delete_points(self, collection: str, point_ids: list[str]) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointIdsList
            QdrantClient(url=self.settings.qdrant_url).delete(collection_name=collection, points_selector=PointIdsList(points=point_ids))
        except Exception:
            logger.exception("Qdrant point deletion failed collection=%s count=%s", collection, len(point_ids))

    def _delete_by_filter(self, collection: str, key: str, value: str) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import FieldCondition, Filter, MatchValue, FilterSelector
            selector = FilterSelector(filter=Filter(must=[FieldCondition(key=key, match=MatchValue(value=value))]))
            QdrantClient(url=self.settings.qdrant_url).delete(collection_name=collection, points_selector=selector)
        except Exception:
            logger.exception("Qdrant filtered deletion failed collection=%s key=%s", collection, key)

    def _ensure_collection(self, client, vector_size: int, distance_type, vector_params_type) -> None:
        self._ensure_named_collection(client, self.settings.qdrant_collection, vector_size, distance_type, vector_params_type)

    def _ensure_named_collection(self, client, collection: str, vector_size: int, distance_type, vector_params_type) -> None:
        if not client.collection_exists(collection):
            self._create_named_collection(client, collection, vector_size, distance_type, vector_params_type)
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
        self._create_named_collection(client, collection, vector_size, distance_type, vector_params_type)

    def _create_collection(self, client, vector_size: int, distance_type, vector_params_type) -> None:
        self._create_named_collection(client, self.settings.qdrant_collection, vector_size, distance_type, vector_params_type)

    def _create_named_collection(self, client, collection: str, vector_size: int, distance_type, vector_params_type) -> None:
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
