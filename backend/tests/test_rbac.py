import uuid

from fastapi.testclient import TestClient

from backend.app.auth.models import Tenant, TenantMembership, User
from backend.app.auth.security import create_access_token, hash_password
from backend.app.db import SessionLocal
from backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _create_user(role: str):
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


def test_viewer_cannot_post():
    headers = _create_user("viewer")
    r = client.post(
        "/api/v1/analytics/reports",
        headers=headers,
        json={"name": "test", "code": "T1", "query": "SELECT 1"},
    )
    assert r.status_code == 403


def test_viewer_can_get_analytics():
    headers = _create_user("viewer")
    r = client.get("/api/v1/analytics/reports", headers=headers)
    assert r.status_code == 200


def test_admin_can_access_everything():
    headers = _create_user("admin")
    r = client.get("/api/v1/settings", headers=headers)
    assert r.status_code == 200


def test_no_token_passes_through_rbac():
    r = client.get("/api/v1/settings")
    assert r.status_code in (401, 403)
