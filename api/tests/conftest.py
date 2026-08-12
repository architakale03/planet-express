import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    # Runs against real Postgres either way: `make test` execs into the api
    # container, `make local-test` runs on the host. No mocks — the point of
    # these tests is that the wiring holds.
    return TestClient(app)
