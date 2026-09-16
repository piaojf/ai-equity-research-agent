from datetime import date

import httpx
import pytest
from pydantic import TypeAdapter

from app.providers.sec.base import FilingMetadata
from app.providers.sec.edgar import SECEDGARProvider
from app.rag.chunking import chunk_filing
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.service import SECAskService
from app.rag.vector_store import InMemoryVectorStore


def _filing(ticker: str = "NVDA") -> FilingMetadata:
    return FilingMetadata(
        ticker=ticker,
        filing_type="10-K",
        filing_date=date(2025, 1, 31),
        accession_number="0000000000-25-000001",
        source_url=TypeAdapter(str).validate_python(
            "https://www.sec.gov/Archives/filing.html"
        ),
    )


@pytest.mark.asyncio
async def test_edgar_adapter_maps_submission_metadata_without_network() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["10-K", "8-K"],
                        "filingDate": ["2025-01-31", "2025-02-01"],
                        "accessionNumber": [
                            "0000000000-25-000001",
                            "0000000000-25-000002",
                        ],
                        "primaryDocument": ["annual.htm", "event.htm"],
                    }
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = SECEDGARProvider(
        "research@example.test",
        ticker_ciks={"NVDA": "1045810"},
        client=client,
    )

    filings = await provider.list_filings("nvda", ["10-K"])
    await client.aclose()

    assert len(filings) == 1
    assert filings[0].filing_type == "10-K"
    assert filings[0].accession_number == "0000000000-25-000001"
    assert seen[0].headers["user-agent"] == "research@example.test"


@pytest.mark.asyncio
async def test_edgar_adapter_resolves_unmapped_ticker_without_network() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url == httpx.URL("https://www.sec.gov/files/company_tickers.json"):
            return httpx.Response(
                200,
                json={"0": {"cik_str": 2488, "ticker": "AMD", "title": "AMD"}},
            )
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "filingDate": ["2025-02-26"],
                        "accessionNumber": ["0000000000-25-000001"],
                        "primaryDocument": ["annual.htm"],
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SECEDGARProvider("research@example.test", client=client)
        filings = await provider.list_filings("AMD", ["10-K"])

    assert filings[0].accession_number == "0000000000-25-000001"
    assert requested == [
        "https://www.sec.gov/files/company_tickers.json",
        "https://data.sec.gov/submissions/CIK0000002488.json",
    ]


@pytest.mark.asyncio
async def test_edgar_adapter_caches_the_full_ticker_directory() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url == httpx.URL("https://www.sec.gov/files/company_tickers.json"):
            return httpx.Response(
                200,
                json={
                    "0": {"cik_str": 2488, "ticker": "AMD", "title": "AMD"},
                    "1": {"cik_str": 1234, "ticker": "ZZZ", "title": "ZZZ"},
                },
            )
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "filingDate": ["2025-02-26"],
                        "accessionNumber": ["0000000000-25-000001"],
                        "primaryDocument": ["annual.htm"],
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = SECEDGARProvider("research@example.test", client=client)
        await provider.list_filings("AMD", ["10-K"])
        filings = await provider.list_filings("ZZZ", ["10-K"])

    assert filings[0].accession_number == "0000000000-25-000001"
    assert requested.count("https://www.sec.gov/files/company_tickers.json") == 1


@pytest.mark.asyncio
async def test_sec_ask_preserves_filing_identity_and_citation() -> None:
    class Answerer:
        async def answer(self, question, evidence):  # noqa: ANN001
            assert question == "What are the risks?"
            assert evidence
            return "The filing identifies operating risks."

    service = SECAskService(
        provider=object(),  # type: ignore[arg-type]
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        answerer=Answerer(),
    )
    await service.ingest(
        _filing(),
        "Item 1A Risk Factors: The company faces supply chain and market risks.",
    )

    result = await service.ask("NVDA", "What are the risks?")

    assert result.confidence == "medium"
    assert result.answer.startswith("The filing")
    assert len(result.citations) == 1
    assert result.citations[0].accession_number == "0000000000-25-000001"
    assert result.citations[0].source_url == _filing().source_url


@pytest.mark.asyncio
async def test_sec_ask_returns_low_confidence_without_evidence() -> None:
    service = SECAskService(
        provider=object(),  # type: ignore[arg-type]
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )

    result = await service.ask("AAPL", "What are the risks?")

    assert result.confidence == "low"
    assert result.citations == []
    assert "sufficient evidence" in result.answer


@pytest.mark.asyncio
async def test_latest_filing_ingestion_prefers_annual_filing() -> None:
    fetched: list[str] = []

    class Provider:
        async def list_filings(
            self, ticker: str, forms: list[str]
        ) -> list[FilingMetadata]:
            del ticker, forms
            return [
                _filing().model_copy(update={"filing_type": "10-Q"}),
                _filing().model_copy(update={"filing_type": "10-K"}),
            ]

        async def fetch_filing(self, filing: FilingMetadata) -> str:
            fetched.append(filing.filing_type)
            return "Item 1A Risk Factors: annual filing evidence."

    service = SECAskService(
        provider=Provider(),  # type: ignore[arg-type]
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )

    await service.ensure_latest_filing_ingested("AMD")

    assert fetched == ["10-K"]


@pytest.mark.asyncio
async def test_latest_filing_ingestion_falls_back_to_current_report() -> None:
    requested_forms: list[str] = []
    fetched: list[str] = []

    class Provider:
        async def list_filings(
            self, ticker: str, forms: list[str]
        ) -> list[FilingMetadata]:
            del ticker
            requested_forms.extend(forms)
            return [_filing().model_copy(update={"filing_type": "8-K"})]

        async def fetch_filing(self, filing: FilingMetadata) -> str:
            fetched.append(filing.filing_type)
            return "Current report evidence."

    service = SECAskService(
        provider=Provider(),  # type: ignore[arg-type]
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )

    await service.ensure_latest_filing_ingested("SPCX")

    assert requested_forms == ["10-K", "10-Q", "8-K", "20-F", "6-K", "40-F"]
    assert fetched == ["8-K"]


def test_chunking_strips_html_and_rejects_invalid_overlap() -> None:
    chunks = chunk_filing(
        _filing(), "<p>Risk&nbsp; factors</p>", chunk_size=30, overlap=2
    )

    assert chunks[0].text == "Risk&nbsp; factors"
    with pytest.raises(ValueError):
        chunk_filing(_filing(), "text", chunk_size=10, overlap=10)
