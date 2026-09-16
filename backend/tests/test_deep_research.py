from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter

from app.core.config import Settings
from app.db.session import Database
from app.deep_research.graph import DeepResearchGraph
from app.providers.market_price.registry import MarketProviderRegistry
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
