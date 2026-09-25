from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_projects_list():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/construction/projects", headers=h)
    assert r.status_code == 200


def test_boqs_list():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/construction/boqs", headers=h)
    assert r.status_code == 200


def test_contracts_list():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/construction/contracts", headers=h)
    assert r.status_code == 200
