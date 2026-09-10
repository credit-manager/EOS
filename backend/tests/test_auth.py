from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_register_login_and_current_identity() -> None:
    email = "owner@example.com"
    password = "Correct-Horse-Battery-42"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "tenant_name": "Acme Construction"},
    )
    assert registered.status_code == 201
    token = registered.json()
    assert token["token_type"] == "bearer"
    tenant_id = UUID(token["tenant_id"])

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["tenant_id"] == str(tenant_id)
    assert me.json()["role"] == "admin"

    login = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert login.status_code == 200
    assert login.json()["tenant_id"] == str(tenant_id)


def test_invalid_or_missing_access_token_is_rejected() -> None:
    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401

    forged = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ4In0.invalid"},
    )
    assert forged.status_code == 401


def test_registration_enforces_strong_password_and_unique_email() -> None:
    payload = {"email": "duplicate@example.com", "password": "Correct-Horse-Battery-42", "tenant_name": "One"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409

    weak = {"email": "weak@example.com", "password": "short", "tenant_name": "Weak"}
    assert client.post("/api/v1/auth/register", json=weak).status_code == 422
