from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "2to-eos"}
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_request_id_is_preserved() -> None:
    request_id = "test-request-123"
    response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_version_contract() -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json()["name"] == "2TO EOS"
