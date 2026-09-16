from datetime import date

import pytest
from pydantic import TypeAdapter
from qdrant_client import AsyncQdrantClient

from app.providers.sec.base import FilingMetadata
from app.rag.chunking import chunk_filing
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.vector_store import QdrantVectorStore


@pytest.mark.asyncio
async def test_qdrant_store_upsert_is_idempotent_and_rehydrates_metadata() -> None:
    client = AsyncQdrantClient(location=":memory:")
    store = QdrantVectorStore("http://unused", client=client)
    filing = FilingMetadata(
        ticker="NVDA",
        filing_type="10-K",
        filing_date=date(2025, 1, 31),
        accession_number="0000000000-25-000001",
        source_url=TypeAdapter(str).validate_python(
            "https://www.sec.gov/Archives/filing.html"
        ),
    )
    chunks = chunk_filing(
        filing,
        "Item 1A Risk Factors: supply chain and market risks.",
        chunk_size=100,
        overlap=10,
    )
    vectors = await DeterministicEmbeddingProvider().embed(
        [chunk.text for chunk in chunks]
    )

    await store.upsert(chunks, vectors)
    await store.upsert(chunks, vectors)
    results = await store.search(vectors[0], ticker="nvda", limit=5)

    assert len(results) == 1
    assert results[0].chunk.chunk_id == chunks[0].chunk_id
    assert results[0].chunk.metadata.accession_number == filing.accession_number
    assert results[0].chunk.text == chunks[0].text
    await client.close()
