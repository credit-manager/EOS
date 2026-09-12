"""S1 authentication security regression tests.

Covers: credential rejection without user enumeration, inactive users,
expired/tampered sessions, cross-tenant membership enforcement,
brute-force rate limiting, and login audit events.
"""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import db as db_module
from backend.app.audit.models import AuditEvent
from backend.app.auth.models import User
from backend.app.main import app

client = TestClient(app)

_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str, password: str = _PASSWORD) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    return response.json()


def test_invalid_password_and_unknown_user_are_indistinguishable() -> None:
    _register("s1-enum@example.com")
    wrong_password = client.post(
        "/api/v1/auth/token",
        json={"email": "s1-enum@example.com", "password": "Wrong-Password-000"},
    )
    unknown_user = client.post(
        "/api/v1/auth/token",
        json={"email": "s1-unknown-user@example.com", "password": "Wrong-Password-000"},
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_inactive_user_cannot_authenticate() -> None:
    token = _register("s1-inactive@example.com")
    session = db_module.SessionLocal()
    try:
        user = session.scalar(select(User).where(User.email == "s1-inactive@example.com"))
        assert user is not None
        user.is_active = False
        session.commit()
    finally:
        session.close()
    login = client.post(
        "/api/v1/auth/token",
        json={"email": "s1-inactive@example.com", "password": _PASSWORD},
    )
    assert login.status_code == 401
    stale = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert stale.status_code == 403


def test_expired_session_is_rejected() -> None:
    from datetime import datetime

    from backend.app.auth.models import AuthSession as SessionModel

    token = _register("s1-expired@example.com")
    session = db_module.SessionLocal()
    try:
        row = session.scalar(
            select(SessionModel).where(
                SessionModel.user_id == UUID(token["user_id"]),
            )
        )
        assert row is not None
        row.expires_at = datetime(2000, 1, 1)
        session.commit()
    finally:
        session.close()
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert me.status_code == 401


def test_logout_is_audited_and_revokes() -> None:
    token = _register("s1-logout-audit@example.com")
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    session = db_module.SessionLocal()
    try:
        events = (
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.tenant_id == UUID(token["tenant_id"]),
                    AuditEvent.action == "auth.logout",
                )
            ).all()
        )
        assert any(
            event.actor_id == UUID(token["user_id"]) and event.request_id
            for event in events
        )
    finally:
        session.close()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_tampered_token_claims_are_rejected() -> None:
    import base64
    import json

    token = _register("s1-tamper@example.com")
    header, payload, signature = token["access_token"].split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "member"
    forged_payload = base64.urlsafe_b64encode(
        json.dumps(claims, separators=(",", ":")).encode()
    ).rstrip(b"=").decode("ascii")
    forged = f"{header}.{forged_payload}.{signature}"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert me.status_code == 401


def test_token_from_another_tenant_cannot_list_members() -> None:
    admin_a = _register("s1-tenant-a@example.com")
    admin_b = _register("s1-tenant-b@example.com")
    headers_b = {"Authorization": f"Bearer {admin_b['access_token']}"}
    members = client.get("/api/v1/auth/members", headers=headers_b)
    assert members.status_code == 200
    emails = {item["email"] for item in members.json()}
    assert "s1-tenant-a@example.com" not in emails
    assert admin_a["tenant_id"] != admin_b["tenant_id"]


def test_login_with_unrelated_tenant_id_is_forbidden() -> None:
    admin_a = _register("s1-tenant-a2@example.com")
    admin_b = _register("s1-tenant-b2@example.com")
    login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "s1-tenant-b2@example.com",
            "password": _PASSWORD,
            "tenant_id": admin_a["tenant_id"],
        },
    )
    assert login.status_code == 403
    assert admin_b["tenant_id"] != admin_a["tenant_id"]


def test_auth_rate_limit_blocks_credential_burst(monkeypatch) -> None:
    from backend.app import main as main_module

    _register("s1-ratelimit@example.com")
    monkeypatch.setattr(
        main_module.settings, "rate_limit_auth_per_minute", 3, raising=False
    )
    main_module._RATE_LIMIT_STATE.clear()
    try:
        for _ in range(3):
            response = client.post(
                "/api/v1/auth/token",
                json={"email": "s1-ratelimit@example.com", "password": "Wrong-Password-000"},
            )
            assert response.status_code == 401
        blocked = client.post(
            "/api/v1/auth/token",
            json={"email": "s1-ratelimit@example.com", "password": "Wrong-Password-000"},
        )
        assert blocked.status_code == 429
        assert blocked.headers.get("Retry-After") is not None
    finally:
        main_module._RATE_LIMIT_STATE.clear()


def test_login_success_and_failure_are_audited() -> None:
    token = _register("s1-audit@example.com")
    tenant_id = UUID(token["tenant_id"])
    user_id = UUID(token["user_id"])

    failed = client.post(
        "/api/v1/auth/token",
        json={"email": "s1-audit@example.com", "password": "Wrong-Password-000"},
    )
    assert failed.status_code == 401
    session = db_module.SessionLocal()
    try:
        failures = (
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.action == "auth.login_failed",
                )
            ).all()
        )
        assert any(event.actor_id == user_id for event in failures)

        ok = client.post(
            "/api/v1/auth/token",
            json={"email": "s1-audit@example.com", "password": _PASSWORD},
        )
        assert ok.status_code == 200
        logins = (
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.action == "auth.login",
                )
            ).all()
        )
        assert any(
            event.actor_id == user_id and event.request_id for event in logins
        )
    finally:
        session.close()
