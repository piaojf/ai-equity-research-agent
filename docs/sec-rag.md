# SEC Filing RAG

Phase 6 keeps SEC filing access behind `SECProvider` and separates ingestion
from retrieval:

```text
SEC EDGAR -> FilingMetadata -> fetch -> clean -> chunk -> embed -> vector store
Question -> embedding -> ticker/filing filter -> relevant chunks -> citations
```

`SECEDGARProvider` requires `SEC_USER_AGENT`, maps submissions and filing text
to internal schemas, and sanitizes timeout, rate-limit and HTTP failures. It
does not expose SEC response JSON directly to API clients.

The local mock path uses `DeterministicEmbeddingProvider` and
`InMemoryVectorStore`. Real mode uses `QdrantVectorStore` behind the same
`VectorStore` protocol, with deterministic point IDs and filing identity fields
stored in payloads.

Every answer citation preserves ticker, filing type, filing date, accession
number, section, chunk ID, source URL and excerpt. If retrieval returns no
evidence, the service returns an explicit insufficient-evidence answer with
`confidence=low`; it does not invent an answer.

The real-mode `POST /api/sec/ask` route lazily ingests the latest SEC filing,
upserts its chunks into Qdrant, retrieves evidence from Qdrant, and constructs
citations from the retrieved filing metadata.
