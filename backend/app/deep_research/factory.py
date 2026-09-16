from datetime import UTC, date, datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.deep_research.graph import DeepResearchGraph
from app.deep_research.llm import StructuredDeepResearchAnswerer
from app.providers.exceptions import ProviderError
from app.providers.llm.openai_compatible import OpenAICompatibleProvider
from app.providers.sec.edgar import SECEDGARProvider
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.service import SECAskService
from app.rag.vector_store import QdrantVectorStore
from app.schemas.deep_research import Evidence
from app.services.market import get_market_service

logger = get_logger(__name__)


class QdrantSECEvidenceSearchTool:
    """Use the existing SEC filing collection as Deep Research evidence."""

    def __init__(self, url: str, collection: str, user_agent: str) -> None:
        self.embedder = DeterministicEmbeddingProvider()
        self.store = QdrantVectorStore(
            url,
            collection=collection,
            dimension=self.embedder.dimension,
        )
        self.ingestion = SECAskService(
            SECEDGARProvider(user_agent), self.embedder, self.store
        )

    async def search(
        self,
        ticker: str,
        around: list[date],
        query: str | None = None,
    ) -> list[Evidence]:
        search_query = query or f"{ticker} recent business risks and price decline"
        vector = (await self.embedder.embed([search_query]))[0]
        await self.store.ensure_collection()
        normalized_ticker = ticker.strip().upper()
        retrieved = await self.store.search(
            vector,
            ticker=normalized_ticker,
            limit=5,
        )
        if not retrieved:
            try:
                await self.ingestion.ensure_latest_filing_ingested(normalized_ticker)
                retrieved = await self.store.search(
                    vector,
                    ticker=normalized_ticker,
                    limit=5,
                )
            except ProviderError as exc:
                logger.warning(
                    "deep_research_sec_auto_ingest_failed",
                    extra={
                        "ticker": normalized_ticker,
                        "provider": "sec_edgar",
                        "error_code": exc.code.value,
                    },
                )
        logger.info(
            "deep_research_qdrant_retrieval",
            extra={
                "ticker": normalized_ticker,
                "provider": "qdrant",
                "collection": self.store.collection,
                "embedding_dimension": self.embedder.dimension,
                "query": search_query,
                "ticker_filter": normalized_ticker,
                "filing_filter": "10-K, 10-Q, 8-K, 20-F, 6-K, 40-F",
                "section_filter": None,
                "top_k": 5,
                "score_threshold": None,
                "retrieved_chunk_ids": [item.chunk.chunk_id for item in retrieved],
                "similarity_scores": [round(item.score, 6) for item in retrieved],
                "search_windows": [item.isoformat() for item in around],
            },
        )
        evidence = [
            Evidence(
                evidence_id=item.chunk.chunk_id,
                source="sec_edgar",
                title=(
                    f"{item.chunk.metadata.filing_type} "
                    f"{item.chunk.metadata.accession_number}"
                ),
                url=item.chunk.metadata.source_url,
                published_at=datetime(
                    item.chunk.metadata.filing_date.year,
                    item.chunk.metadata.filing_date.month,
                    item.chunk.metadata.filing_date.day,
                    tzinfo=UTC,
                ),
                summary=item.chunk.text,
                evidence_type="sec",
            )
            for item in retrieved
        ]
        logger.info(
            "deep_research_evidence_normalized",
            extra={
                "ticker": normalized_ticker,
                "provider": "sec_edgar",
                "raw_result_count": len(retrieved),
                "normalized_result_count": len(evidence),
                "discarded_count": len(retrieved) - len(evidence),
                "discard_reason": None,
            },
        )
        return evidence


def build_runtime_deep_research_graph() -> DeepResearchGraph:
    settings = get_settings()
    answerer = None
    if (
        settings.deepseek_api_key is not None
        and settings.deepseek_api_key.get_secret_value().strip()
    ):
        answerer = StructuredDeepResearchAnswerer(
            OpenAICompatibleProvider(
                settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                timeout_seconds=settings.provider_timeout_seconds * 3,
            )
        )
    sec_tool = None
    if settings.data_mode == "real" and settings.sec_user_agent is not None:
        sec_tool = QdrantSECEvidenceSearchTool(
            settings.qdrant_url,
            settings.qdrant_collection,
            settings.sec_user_agent.get_secret_value(),
        )
    return DeepResearchGraph(
        get_market_service(),
        sec_tool=sec_tool,
        answerer=answerer,
    )
