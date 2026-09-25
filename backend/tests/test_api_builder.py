from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def get_token():
    r = client.post("/api/v1/auth/token", json={"email": "test@2to-eos.local", "password": "TestPass12345!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_builder_objects_list():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/builder/objects", headers=h)
    assert r.status_code == 200


def test_builder_objects_create():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/builder/objects", headers=h, json={
        "name": "test_object",
        "label": "Test Object",
        "fields": []
    })
    assert r.status_code in (200, 201, 422)


def test_builder_objects_get():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/builder/objects/test_object", headers=h)
    assert r.status_code in (200, 404)
