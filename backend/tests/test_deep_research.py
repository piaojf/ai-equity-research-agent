from datetime import UTC, date, datetime

import pytest
from pydantic import TypeAdapter

from app.core.config import Settings
from app.db.session import Database
from app.deep_research.factory import QdrantSECEvidenceSearchTool
from app.deep_research.graph import DeepResearchGraph
from app.providers.market_price.registry import MarketProviderRegistry
from app.providers.sec.base import FilingMetadata
from app.rag.chunking import FilingChunk
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.vector_store import RetrievedChunk
from app.schemas.deep_research import Evidence
from app.services.market import MarketService
from app.workers.queue import InMemoryTaskQueue
from app.workers.service import DeepResearchService, DurableDeepResearchService


class EvidenceTool:
    async def search(self, ticker: str, around):  # noqa: ANN001
        del around
        return [
            Evidence(
                evidence_id=f"news:{ticker}",
                source="fixture-news",
                title="Fixture event",
                url=TypeAdapter(str).validate_python("https://example.test/event"),
                published_at=datetime(2026, 9, 14, tzinfo=UTC),
                summary="A verified fixture event was published.",
                evidence_type="news",
            )
        ]


@pytest.mark.asyncio
async def test_deep_research_graph_keeps_evidence_ids_and_confidence() -> None:
    market = MarketService(
        MarketProviderRegistry(Settings(data_mode="mock")),
        Settings(data_mode="mock", provider_retry_delay_seconds=0),
    )
    graph = DeepResearchGraph(market, news_tool=EvidenceTool())

    report = await graph.ainvoke("NVDA", "Why did NVDA move?")

    assert report.ticker == "NVDA"
    assert report.evidence
    assert report.major_events[0].evidence_ids == ["news:NVDA"]
    assert report.confidence == "low"


@pytest.mark.asyncio
async def test_queue_service_returns_queued_then_completed_status() -> None:
    market = MarketService(
        MarketProviderRegistry(Settings(data_mode="mock")),
        Settings(data_mode="mock", provider_retry_delay_seconds=0),
    )
    queue = InMemoryTaskQueue()
    service = DeepResearchService(queue, DeepResearchGraph(market))

    accepted = await service.submit("NVDA", "Why did NVDA move?")
    queued = service.status(accepted.task_id)
    assert queued is not None
    assert queued.status == "queued"

    assert await service.run_once() is True
    completed = service.status(accepted.task_id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.report is not None


def test_deep_research_endpoint_returns_202_and_task_id(client) -> None:  # noqa: ANN001
    response = client.post(
        "/api/deep-research",
        json={"ticker": "NVDA", "question": "Why did NVDA move?"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["request_id"]
    assert payload["data"]["task_id"]
    assert payload["data"]["status"] == "queued"


@pytest.mark.asyncio
async def test_durable_service_persists_task_and_enqueues_request_id() -> None:
    class Queue:
        def __init__(self) -> None:
            self.jobs = []

        async def enqueue(self, job) -> None:  # noqa: ANN001
            self.jobs.append(job)

    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    queue = Queue()
    service = DurableDeepResearchService(database, queue)

    accepted = await service.submit(
        "nvda", "Why did NVDA move?", request_id="req-durable"
    )
    status = await service.status(accepted.task_id)

    assert status is not None
    assert status.status == "queued"
    assert queue.jobs[0].task_id == accepted.task_id
    assert queue.jobs[0].request_id == "req-durable"
    await database.dispose()


@pytest.mark.asyncio
async def test_deep_research_retrieves_quarterly_filings_for_any_sec_ticker() -> None:
    class Store:
        collection = "sec_filing_chunks"

        def __init__(self) -> None:
            self.filing_filters: list[str | None] = []

        async def ensure_collection(self) -> None:
            return None

        async def search(
            self,
            vector: list[float],
            *,
            ticker: str,
            filing_type: str | None = None,
            limit: int = 5,
        ) -> list[RetrievedChunk]:
            del vector, ticker, limit
            self.filing_filters.append(filing_type)
            if len(self.filing_filters) == 1:
                return []
            filing = FilingMetadata(
                ticker="SPCX",
                filing_type="10-Q",
                filing_date=date(2026, 8, 4),
                accession_number="0001628280-26-052535",
                source_url=TypeAdapter(str).validate_python(
                    "https://www.sec.gov/Archives/edgar/data/1181412/spcx-20260630.htm"
                ),
            )
            chunk = FilingChunk(
                chunk_id="0001628280-26-052535:filing:0",
                metadata=filing,
                section="filing",
                text="Quarterly filing evidence.",
            )
            return [RetrievedChunk(chunk=chunk, score=0.91)]

    class Ingestion:
        def __init__(self) -> None:
            self.tickers: list[str] = []

        async def ensure_latest_filing_ingested(self, ticker: str) -> None:
            self.tickers.append(ticker)

    tool = object.__new__(QdrantSECEvidenceSearchTool)
    tool.embedder = DeterministicEmbeddingProvider()
    tool.store = Store()  # type: ignore[assignment]
    tool.ingestion = Ingestion()  # type: ignore[assignment]

    evidence = await tool.search("spcx", [], "最近有哪些重大事项？")

    assert tool.store.filing_filters == [None, None]
    assert tool.ingestion.tickers == ["SPCX"]
    assert evidence[0].evidence_type == "sec"
    assert evidence[0].title.startswith("10-Q")
