from fastapi.testclient import TestClient


def test_public_mock_endpoints_and_docs_are_available(client: TestClient) -> None:
    health = client.get("/health")
    stock = client.get("/api/stocks/NVDA")
    sec = client.post(
        "/api/sec/ask",
        json={"ticker": "NVDA", "question": "What are the main risks?"},
    )
    research = client.get("/api/research/NVDA")
    deep_research = client.post(
        "/api/deep-research",
        json={"ticker": "NVDA", "question": "Why did NVDA move?"},
    )

    assert health.status_code == 200
    assert stock.status_code == 200
    assert sec.status_code == 200
    assert research.status_code == 200
    assert deep_research.status_code == 202
    for response in (health, stock, sec, research, deep_research):
        assert response.json()["request_id"]

    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
