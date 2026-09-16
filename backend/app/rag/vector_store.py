from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from pydantic import HttpUrl, TypeAdapter
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.providers.sec.base import FilingMetadata
from app.rag.chunking import FilingChunk


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk: FilingChunk
    score: float


class VectorStore(Protocol):
    async def upsert(
        self, chunks: list[FilingChunk], vectors: list[list[float]]
    ) -> None: ...

    async def search(
        self,
        vector: list[float],
        *,
        ticker: str,
        filing_type: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]: ...


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: list[tuple[FilingChunk, list[float]]] = []

    async def upsert(
        self, chunks: list[FilingChunk], vectors: list[list[float]]
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        self._items = [
            (chunk, vector)
            for chunk, vector in self._items
            if chunk.chunk_id not in {item.chunk_id for item in chunks}
        ]
        self._items.extend(zip(chunks, vectors, strict=True))

    async def search(
        self,
        vector: list[float],
        *,
        ticker: str,
        filing_type: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        if limit <= 0:
            return []
        normalized = ticker.strip().upper()
        matches: list[RetrievedChunk] = []
        for chunk, candidate in self._items:
            if chunk.metadata.ticker != normalized:
                continue
            if filing_type is not None and chunk.metadata.filing_type != filing_type:
                continue
            denominator = math.sqrt(sum(value * value for value in vector)) * math.sqrt(
                sum(value * value for value in candidate)
            )
            score = (
                sum(left * right for left, right in zip(vector, candidate, strict=True))
                / denominator
                if denominator
                else 0.0
            )
            matches.append(RetrievedChunk(chunk=chunk, score=score))
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:limit]


class QdrantVectorStore:
    """Qdrant-backed implementation of the shared vector-store port."""

    def __init__(
        self,
        url: str,
        *,
        collection: str = "sec_filing_chunks",
        dimension: int = 32,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        self.client = client or AsyncQdrantClient(url=url)
        self.collection = collection
        self.dimension = dimension

    async def ensure_collection(self) -> None:
        if not await self.client.collection_exists(collection_name=self.collection):
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(
                    size=self.dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            return
        info = await self.client.get_collection(self.collection)
        vectors = info.config.params.vectors
        if isinstance(vectors, qmodels.VectorParams):
            if (
                vectors.size != self.dimension
                or vectors.distance != qmodels.Distance.COSINE
            ):
                raise ValueError(
                    "Qdrant collection vector configuration does not match "
                    "the configured embedding provider."
                )

    async def upsert(
        self, chunks: list[FilingChunk], vectors: list[list[float]]
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        await self.ensure_collection()
        points = [
            qmodels.PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "ticker": chunk.metadata.ticker,
                    "filing_type": chunk.metadata.filing_type,
                    "filing_date": chunk.metadata.filing_date.isoformat(),
                    "accession_number": chunk.metadata.accession_number,
                    "source_url": str(chunk.metadata.source_url),
                    "section": chunk.section,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self.client.upsert(collection_name=self.collection, points=points)

    async def search(
        self,
        vector: list[float],
        *,
        ticker: str,
        filing_type: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        if limit <= 0:
            return []
        conditions: list[Any] = [
            qmodels.FieldCondition(
                key="ticker",
                match=qmodels.MatchValue(value=ticker.strip().upper()),
            )
        ]
        if filing_type is not None:
            conditions.append(
                qmodels.FieldCondition(
                    key="filing_type",
                    match=qmodels.MatchValue(value=filing_type),
                )
            )
        response = await self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=qmodels.Filter(must=conditions),
            limit=limit,
            with_payload=True,
        )
        results: list[RetrievedChunk] = []
        for point in response.points:
            payload = point.payload or {}
            try:
                metadata = FilingMetadata(
                    ticker=str(payload["ticker"]),
                    filing_type=str(payload["filing_type"]),
                    filing_date=date.fromisoformat(str(payload["filing_date"])),
                    accession_number=str(payload["accession_number"]),
                    source_url=TypeAdapter(HttpUrl).validate_python(
                        str(payload["source_url"])
                    ),
                )
                chunk = FilingChunk(
                    chunk_id=str(payload["chunk_id"]),
                    metadata=metadata,
                    section=str(payload["section"]),
                    text=str(payload["text"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Qdrant returned malformed chunk metadata.") from exc
            results.append(RetrievedChunk(chunk=chunk, score=float(point.score)))
        return results
