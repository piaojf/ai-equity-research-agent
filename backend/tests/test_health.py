from fastapi.testclient import TestClient


def test_health_returns_ok_and_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["data"]["status"] == "ok"
    assert body["data"]["data_mode"] == "mock"
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_health_preserves_incoming_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.json()["request_id"] == "test-request-123"
    assert response.headers["X-Request-ID"] == "test-request-123"
