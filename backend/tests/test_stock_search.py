import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.universe import StockUniverseService


def test_stock_search_returns_mock_directory_matches(client) -> None:  # noqa: ANN001
    response = client.get("/api/stocks/search", params={"q": "nvda"})

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["errors"] == []
    assert body["data"][0]["ticker"] == "NVDA"
    assert body["data"][0]["company_name"] == "NVIDIA Corporation"


def test_stock_search_empty_query_does_not_return_directory(client) -> None:  # noqa: ANN001
    response = client.get("/api/stocks/search")

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_stock_search_parses_sec_directory_without_network(tmp_path) -> None:
    requested: list[httpx.Request] = []

    def response(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(
            200,
            json={
                "0": {"cik_str": 1, "ticker": "ZZZ", "title": "Zeta Zone, Inc."},
                "1": {"cik_str": 2, "ticker": "AAA", "title": "Alpha Analytics"},
            },
        )

    settings = Settings(
        data_mode="real",
        sec_user_agent=SecretStr("research@example.test"),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        service = StockUniverseService(
            settings,
            client=client,
            cache_path=tmp_path / "directory.json",
        )
        results = await service.search("zzz")

    assert [item.ticker for item in results] == ["ZZZ"]
    assert requested[0].headers["user-agent"] == "research@example.test"
