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

The local development path uses `DeterministicEmbeddingProvider` and
`InMemoryVectorStore`. Production can replace those ports with an embedding
provider and Qdrant without changing `SECAskService`.

Every answer citation preserves ticker, filing type, filing date, accession
number, section, chunk ID, source URL and excerpt. If retrieval returns no
evidence, the service returns an explicit insufficient-evidence answer with
`confidence=low`; it does not invent an answer.

The Qdrant deployment and `POST /api/sec/ask` route are wired in the later
integration phase after persistence and API dependency wiring stabilize.
