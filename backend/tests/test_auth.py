from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

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


def test_logout_revokes_only_the_current_session() -> None:
    email = "session@example.com"
    password = "Correct-Horse-Battery-42"
    registered = _register(email, password)
    second = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert second.status_code == 200

    first_headers = {"Authorization": f"Bearer {registered['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=first_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=second_headers).status_code == 200

    logout = client.post("/api/v1/auth/logout", headers=first_headers)
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me", headers=first_headers).status_code == 401
    assert client.get("/api/v1/auth/me", headers=second_headers).status_code == 200

    repeated = client.post("/api/v1/auth/logout", headers=first_headers)
    assert repeated.status_code == 401


def test_refresh_rotates_session_and_rejects_reuse() -> None:
    registered = _register("refresh@example.com")

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["user_id"] == registered["user_id"]
    assert body["tenant_id"] == registered["tenant_id"]
    assert body["role"] == "admin"
    assert body["access_token"] != registered["access_token"]
    assert body["refresh_token"] != registered["refresh_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["tenant_id"] == body["tenant_id"]

    old_access = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )
    assert old_access.status_code == 401

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert reused.status_code == 401


def test_refresh_unique_session_lookup_does_not_match_other_sessions() -> None:
    first = _register("refresh-first@example.com")
    second = _register("refresh-second@example.com")

    with_first = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert with_first.status_code == 200
    assert with_first.json()["user_id"] == first["user_id"]

    with_second = client.post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert with_second.status_code == 200
    assert with_second.json()["user_id"] == second["user_id"]

    guess = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert guess.status_code == 401


def test_expired_refresh_token_is_rejected() -> None:
    from datetime import datetime

    from backend.app.auth.models import AuthSession
    from backend.app.auth.security import hash_token
    from backend.app.db import SessionLocal

    registered = _register("refresh-expired@example.com")
    session = SessionLocal()
    try:
        row = session.scalar(
            select(AuthSession).where(
                AuthSession.user_id == UUID(registered["user_id"]),
            )
        )
        assert row is not None
        assert row.refresh_token_hash == hash_token(registered["refresh_token"])
        row.refresh_expires_at = datetime(2000, 1, 1)
        session.commit()
    finally:
        session.close()

    expired = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert expired.status_code == 401


def test_refresh_keeps_tenant_binding_without_escalation() -> None:
    owner_a = _register("refresh-tenant-a@example.com")
    owner_b = _register("refresh-tenant-b@example.com")

    admin_headers = {"Authorization": f"Bearer {owner_a['access_token']}"}
    added = client.post(
        "/api/v1/auth/members",
        json={"email": "refresh-tenant-b@example.com", "role": "member"},
        headers=admin_headers,
    )
    assert added.status_code == 201

    login_b_in_a = client.post(
        "/api/v1/auth/token",
        json={
            "email": "refresh-tenant-b@example.com",
            "password": "Correct-Horse-Battery-42",
            "tenant_id": owner_a["tenant_id"],
        },
    )
    assert login_b_in_a.status_code == 200

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_b_in_a.json()["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["tenant_id"] == owner_a["tenant_id"]
    assert refreshed.json()["user_id"] == owner_b["user_id"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["tenant_id"] == owner_a["tenant_id"]
    assert me.json()["role"] == "member"


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
