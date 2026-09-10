from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _register(email: str, password: str = "Correct-Horse-Battery-42") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    return response.json()


def test_register_login_and_current_identity() -> None:
    email = "owner@example.com"
    password = "Correct-Horse-Battery-42"
    token = _register(email, password)
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


def test_admin_can_add_member_and_protect_last_admin() -> None:
    admin = _register("admin@example.com")
    member = _register("member@example.com")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    added = client.post(
        "/api/v1/auth/members",
        json={"email": "member@example.com", "role": "member"},
        headers=admin_headers,
    )
    assert added.status_code == 201
    assert added.json()["role"] == "member"

    member_login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "member@example.com",
            "password": "Correct-Horse-Battery-42",
            "tenant_id": admin["tenant_id"],
        },
    )
    assert member_login.status_code == 200
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}
    assert client.get("/api/v1/auth/members", headers=member_headers).status_code == 403

    member_id = UUID(added.json()["user_id"])
    promoted = client.patch(
        f"/api/v1/auth/members/{member_id}",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert promoted.status_code == 200

    admins = client.get("/api/v1/auth/members", headers=admin_headers).json()
    assert sum(item["role"] == "admin" for item in admins) == 2

    demoted = client.patch(
        f"/api/v1/auth/members/{member_id}",
        json={"role": "member"},
        headers=admin_headers,
    )
    assert demoted.status_code == 200

    admin_id = UUID(admin["user_id"])
    last_admin = client.patch(
        f"/api/v1/auth/members/{admin_id}",
        json={"role": "member"},
        headers=admin_headers,
    )
    assert last_admin.status_code == 409
    assert member["tenant_id"] != admin["tenant_id"]
