import logging

import pytest
from fastapi.testclient import TestClient


def test_request_completion_log_contains_required_fields(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        response = client.get("/health")

    assert response.status_code == 200
    records = [
        record for record in caplog.records if record.message == "request_completed"
    ]
    assert records
    record = records[-1]
    assert record.request_id == response.json()["request_id"]
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert isinstance(record.latency_ms, float)
