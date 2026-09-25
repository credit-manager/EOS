import uuid

from fastapi.testclient import TestClient

from backend.app.auth.models import Tenant, TenantMembership, User
from backend.app.auth.security import create_access_token, hash_password
from backend.app.db import SessionLocal
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _setup(role="admin"):
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant")
    db = SessionLocal()
    db.add(tenant)
    db.flush()
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4()}@example.com",
        password_hash=hash_password("TestPass12345!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    membership = TenantMembership(
        tenant_id=tenant.id, user_id=user.id, role=role
    )
    db.add(membership)
    access, _, session = create_access_token(
        user_id=user.id, tenant_id=tenant.id, role=role
    )
    db.add(session)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {access}"}


def test_get_settings_returns_200():
    headers = _setup()
    r = client.get("/api/v1/settings", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "tenant_id" in body
    assert "company_name" in body
    assert "timezone" in body
    assert "currency" in body


def test_patch_settings_returns_200():
    headers = _setup()
    r = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"company_name": "Acme Corp", "timezone": "America/New_York"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["company_name"] == "Acme Corp"
    assert body["timezone"] == "America/New_York"


def test_get_settings_without_auth():
    r = client.get("/api/v1/settings")
    assert r.status_code in (401, 403)


def test_patch_settings_without_auth():
    r = client.patch("/api/v1/settings", json={"company_name": "No Auth"})
    assert r.status_code in (401, 403)
