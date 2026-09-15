def test_sec_ask_returns_low_confidence_without_evidence(
    client,  # noqa: ANN001
) -> None:
    response = client.post(
        "/api/sec/ask",
        json={"ticker": "NVDA", "question": "What are the major risks?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["data"]["confidence"] == "low"
    assert payload["data"]["citations"] == []
