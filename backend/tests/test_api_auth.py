from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_token_generation():
    token = get_token()
    assert token is not None
    assert len(token) > 0


def test_me_endpoint():
    token = get_token()
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_invalid_credentials():
    r = client.post("/api/v1/auth/token", json={"email": "bad@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_without_token():
    r = client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)
