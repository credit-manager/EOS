from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_industry_packs():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/marketplace/industry-packs", headers=h)
    assert r.status_code == 200


def test_apps_list():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/marketplace/apps", headers=h)
    assert r.status_code == 200
