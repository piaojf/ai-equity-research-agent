import os

import pytest
from fastapi.testclient import TestClient

# Keep the unit-test suite deterministic even when the developer's local .env
# enables real services for runtime verification.
os.environ["DATA_MODE"] = "mock"

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client
