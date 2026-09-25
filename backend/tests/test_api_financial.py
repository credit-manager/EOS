from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_accounts():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/financial/accounts", headers=h)
    assert r.status_code == 200


def test_customers():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/financial/customers", headers=h)
    assert r.status_code == 200


def test_suppliers():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/financial/suppliers", headers=h)
    assert r.status_code == 200
