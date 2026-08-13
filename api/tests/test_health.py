from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import app


def test_health_is_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_db_health_reaches_postgres(client: TestClient) -> None:
    resp = client.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["postgres_version"].startswith("16")


def test_db_health_returns_503_when_database_unreachable(client: TestClient) -> None:
    """A real failed connection, not a mock: port 1 refuses immediately.

    Overriding get_db is the only seam that does not require taking Postgres
    down for the whole suite. The session it yields is a real Session; the
    failure happens where it would in production, inside db.execute().
    """
    dead = sessionmaker(
        bind=create_engine("postgresql+psycopg://postgres:postgres@127.0.0.1:1/planet_express")
    )

    def get_dead_db() -> Iterator[Session]:
        db = dead()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_dead_db
    try:
        resp = client.get("/health/db")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "database unreachable"
    finally:
        app.dependency_overrides.pop(get_db)
