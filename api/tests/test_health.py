from fastapi.testclient import TestClient


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
