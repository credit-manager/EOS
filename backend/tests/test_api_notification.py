from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_alerts():
    token = get_token()
    r = client.get("/api/v1/notifications/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_stats():
    token = get_token()
    r = client.get("/api/v1/notifications/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
