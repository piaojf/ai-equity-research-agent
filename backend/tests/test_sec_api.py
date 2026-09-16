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


def test_sec_ask_rejects_invalid_ticker_and_filing_type(client) -> None:  # noqa: ANN001
    response = client.post(
        "/api/sec/ask",
        json={
            "ticker": "not a ticker",
            "question": "What are the major risks?",
            "filing_type": "NOT-SEC-FORM",
        },
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "VALIDATION_ERROR"
