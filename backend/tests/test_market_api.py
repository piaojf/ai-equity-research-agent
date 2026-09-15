from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ErrorCode
from app.main import create_app
from app.providers.market_price.registry import MarketProviderRegistry
from app.services.market import MarketService, get_market_service


def test_stock_overview_api_returns_mock_data(client: TestClient) -> None:
    response = client.get("/api/stocks/nvda")

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["data"]["ticker"] == "NVDA"
    assert body["data"]["quote"]["source"] == "mock"
    assert body["data"]["history"]["source"] == "mock"
    assert body["errors"] == []


def test_stock_overview_api_returns_invalid_ticker_error(client: TestClient) -> None:
    response = client.get("/api/stocks/not a ticker")

    assert response.status_code == 400
    body = response.json()
    assert body["errors"][0]["code"] == ErrorCode.INVALID_TICKER
    assert body["request_id"]


def test_real_mode_without_key_returns_configuration_error() -> None:
    application = create_app()
    settings = Settings(data_mode="real")
    application.dependency_overrides[get_market_service] = lambda: MarketService(
        MarketProviderRegistry(settings), settings
    )

    with TestClient(application) as test_client:
        response = test_client.get("/api/stocks/NVDA")

    assert response.status_code == 503
    assert response.json()["errors"][0]["code"] == ErrorCode.CONFIGURATION_ERROR
