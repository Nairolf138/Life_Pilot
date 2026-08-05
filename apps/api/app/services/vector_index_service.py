"""Indexation vectorielle optionnelle des passages documentaires."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.util
import math
import re
from dataclasses import dataclass, field
from typing import Annotated, Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import Depends

from app.core.config import Settings, get_settings

DEFAULT_COLLECTION_NAME = "lifepilot_document_passages"
DEFAULT_VECTOR_SIZE = 384
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True, slots=True)
class DocumentPassage:
    """Passage extrait d'un document et prêt à être indexé."""

    document_id: UUID
    text: str
    chunk_index: int
    source_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """Résultat de recherche retourné à l'assistant avec sa source interne."""

    document_id: UUID
    passage: str
    score: float
    chunk_index: int
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorBackend(Protocol):
    """Contrat minimal d'un stockage vectoriel."""

    async def upsert_passages(self, passages: list[DocumentPassage]) -> None:
        """Indexe ou remplace des passages."""

    async def search(self, query: str, *, limit: int) -> list[VectorSearchResult]:
        """Recherche les passages les plus proches de la requête."""


class VectorIndexService:
    """Service d'indexation désactivable, avec Qdrant optionnel."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._backend: VectorBackend | None = _build_backend(settings)

    @property
    def enabled(self) -> bool:
        """Indique si l'index vectoriel peut être utilisé."""

        return self._backend is not None

    async def index_document_text(
        self,
        *,
        document_id: UUID,
        text: str | None,
        source_label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentPassage]:
        """Découpe et indexe le texte extrait d'un document source."""

        if self._backend is None or not text:
            return []
        passages = [
            DocumentPassage(
                document_id=document_id,
                text=chunk,
                chunk_index=index,
                source_label=source_label,
                metadata=metadata or {},
            )
            for index, chunk in enumerate(chunk_text(text))
        ]
        if passages:
            await self._backend.upsert_passages(passages)
        return passages

    async def search_relevant_passages(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> list[VectorSearchResult]:
        """Retourne des passages pertinents avec sources internes pour l'assistant."""

        if self._backend is None or not query.strip():
            return []
        return await self._backend.search(query, limit=limit)


class InMemoryVectorBackend:
    """Backend local utile en développement quand Qdrant n'est pas configuré."""

    def __init__(self) -> None:
        self._items: list[tuple[list[float], DocumentPassage]] = []

    async def upsert_passages(self, passages: list[DocumentPassage]) -> None:
        identities = {
            (passage.document_id, passage.chunk_index) for passage in passages
        }
        self._items = [
            item
            for item in self._items
            if (item[1].document_id, item[1].chunk_index) not in identities
        ]
        self._items.extend((embed_text(passage.text), passage) for passage in passages)

    async def search(self, query: str, *, limit: int) -> list[VectorSearchResult]:
        query_vector = embed_text(query)
        ranked = sorted(
            (
                (cosine_similarity(query_vector, vector), passage)
                for vector, passage in self._items
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        return [
            _result_from_passage(passage, score)
            for score, passage in ranked[:limit]
        ]


class QdrantVectorBackend:
    """Backend Qdrant chargé dynamiquement pour garder la dépendance optionnelle."""

    def __init__(
        self, *, url: str, collection_name: str = DEFAULT_COLLECTION_NAME
    ) -> None:
        qdrant_client = importlib.import_module("qdrant_client")
        self._models = importlib.import_module("qdrant_client.models")
        self._client = qdrant_client.QdrantClient(url=url)
        self._collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self._client.get_collections().collections
        if any(collection.name == self._collection_name for collection in collections):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=self._models.VectorParams(
                size=DEFAULT_VECTOR_SIZE,
                distance=self._models.Distance.COSINE,
            ),
        )

    async def upsert_passages(self, passages: list[DocumentPassage]) -> None:
        points = [
            self._models.PointStruct(
                id=str(
                    uuid5(
                        NAMESPACE_URL,
                        f"{passage.document_id}:{passage.chunk_index}",
                    )
                ),
                vector=embed_text(passage.text),
                payload={
                    "document_id": str(passage.document_id),
                    "text": passage.text,
                    "chunk_index": passage.chunk_index,
                    "source_label": passage.source_label,
                    "metadata": passage.metadata,
                },
            )
            for passage in passages
        ]
        await asyncio.to_thread(
            self._client.upsert,
            collection_name=self._collection_name,
            points=points,
        )

    async def search(self, query: str, *, limit: int) -> list[VectorSearchResult]:
        hits = await asyncio.to_thread(
            self._client.search,
            collection_name=self._collection_name,
            query_vector=embed_text(query),
            limit=limit,
        )
        return [
            _result_from_payload(hit.payload or {}, float(hit.score))
            for hit in hits
        ]


def _build_backend(settings: Settings) -> VectorBackend | None:
    provider = settings.llm_provider.strip().lower()
    if provider == "none":
        return None
    if settings.qdrant_url and importlib.util.find_spec("qdrant_client") is not None:
        return QdrantVectorBackend(url=settings.qdrant_url)
    return InMemoryVectorBackend()


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Découpe un texte en passages chevauchants et nettoyés."""

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_text(text: str, *, dimensions: int = DEFAULT_VECTOR_SIZE) -> list[float]:
    """Produit un embedding déterministe sans appel réseau pour rester désactivable."""

    vector = [0.0] * dimensions
    for token in re.findall(r"\w+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Calcule une similarité cosinus entre deux vecteurs normalisés ou non."""

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = sum(a * b for a, b in zip(left, right, strict=False))
    return dot_product / (left_norm * right_norm)


def _result_from_passage(passage: DocumentPassage, score: float) -> VectorSearchResult:
    source = (
        passage.source_label
        or f"document:{passage.document_id}#chunk:{passage.chunk_index}"
    )
    return VectorSearchResult(
        document_id=passage.document_id,
        passage=passage.text,
        score=score,
        chunk_index=passage.chunk_index,
        source=source,
        metadata=passage.metadata,
    )


def _result_from_payload(payload: dict[str, Any], score: float) -> VectorSearchResult:
    document_id = UUID(str(payload["document_id"]))
    chunk_index = int(payload.get("chunk_index", 0))
    source_label = payload.get("source_label")
    passage = str(payload.get("text", ""))
    return VectorSearchResult(
        document_id=document_id,
        passage=passage,
        score=score,
        chunk_index=chunk_index,
        source=source_label or f"document:{document_id}#chunk:{chunk_index}",
        metadata=dict(payload.get("metadata") or {}),
    )


async def get_vector_index_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VectorIndexService:
    """Construit le service d'index vectoriel pour FastAPI."""

    return VectorIndexService(settings)
