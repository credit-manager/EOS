from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_version():
    r = client.get("/api/v1/version")
    assert r.status_code == 200


def test_ready():
    r = client.get("/api/v1/ready")
    assert r.status_code == 200
