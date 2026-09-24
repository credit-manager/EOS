from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_graph_stats():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/graph/stats", headers=h)
    assert r.status_code == 200


def test_graph_global():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/graph/global", headers=h)
    assert r.status_code == 200
