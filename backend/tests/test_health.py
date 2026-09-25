from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "2to-eos"
    assert "version" in data
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    assert "circuit_breakers" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert data["status"] in ("ok", "degraded", "critical")
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_request_id_is_preserved() -> None:
    request_id = "test-request-123"
    response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_invalid_request_id_is_replaced() -> None:
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "invalid request id with spaces"},
    )
    assert response.status_code == 200
    returned = response.headers["X-Request-ID"]
    assert returned != "invalid request id with spaces"
    assert returned
    assert all(character in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-" for character in returned)


def test_version_contract() -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "2TO EOS"
    assert "version" in data


def test_ready_endpoint() -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "database" in data
    assert "redis" in data
    assert isinstance(data["ready"], bool)
    assert isinstance(data["database"], bool)
    assert isinstance(data["redis"], bool)
