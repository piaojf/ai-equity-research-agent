from fastapi import APIRouter, Query
from fastapi.testclient import TestClient

from app.core.errors import AppError, ErrorCode
from app.main import create_app


def test_not_found_uses_error_response(client: TestClient) -> None:
    response = client.get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["request_id"]
    assert body["errors"][0]["code"] == ErrorCode.HTTP_ERROR


def test_app_error_uses_error_response() -> None:
    application = create_app()
    router = APIRouter()

    @router.get("/test-error")
    async def test_error() -> None:
        raise AppError(
            code=ErrorCode.PROVIDER_TIMEOUT,
            message="Provider timed out.",
            status_code=504,
            retryable=True,
        )

    application.include_router(router)
    with TestClient(application) as client:
        response = client.get("/test-error")

    assert response.status_code == 504
    body = response.json()
    assert body["request_id"]
    assert body["errors"] == [
        {
            "code": "PROVIDER_TIMEOUT",
            "message": "Provider timed out.",
            "retryable": True,
            "details": None,
        }
    ]


def test_validation_error_uses_error_response() -> None:
    application = create_app()
    router = APIRouter()

    @router.get("/validated")
    async def validated(limit: int = Query(ge=1)) -> dict[str, int]:
        return {"limit": limit}

    application.include_router(router)
    with TestClient(application) as client:
        response = client.get("/validated", params={"limit": "invalid"})

    assert response.status_code == 422
    body = response.json()
    assert body["request_id"]
    assert body["errors"][0]["code"] == "VALIDATION_ERROR"
