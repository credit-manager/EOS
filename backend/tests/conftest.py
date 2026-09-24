import os

# Force SQLite for tests regardless of .env
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./eos_test.db"

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db as db_module
from backend.app.db import Base, get_db

TEST_PASSWORD = "TestPass12345!"


@pytest.fixture(autouse=True, scope="session")
def _create_all_tables():
    if "sqlite" in db_module.engine.url.drivername:
        new_engine = create_engine(
            db_module.engine.url,
            future=True,
            pool_pre_ping=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        db_module.engine.dispose()
        db_module.engine = new_engine
        db_module.SessionLocal.configure(bind=new_engine)
    Base.metadata.drop_all(bind=db_module.engine)
    Base.metadata.create_all(bind=db_module.engine)
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear in-memory rate-limit buckets between tests.

    Production middleware enforces per-tenant/per-route limits; the full
    test suite issues far more requests per 60s window than a real tenant
    would. Resetting between tests keeps rate limiting active (so security
    tests that assert on it still pass) without cross-test pollution.
    """
    from backend.app.main import reset_rate_limit_state

    reset_rate_limit_state()
    yield
    reset_rate_limit_state()


@pytest.fixture(autouse=True, scope="session")
def _seed_user():
    from backend.app.auth.security import hash_password
    from backend.app.auth.models import User, Tenant, TenantMembership

    with db_module.engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = 'test@2to-eos.local' LIMIT 1")
        ).fetchone()
        if existing is not None:
            return

    with Session(bind=db_module.engine) as session:
        tenant = Tenant(name="Test Tenant")
        session.add(tenant)
        session.flush()
        user = User(
            email="test@2to-eos.local",
            password_hash=hash_password(TEST_PASSWORD),
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin"))
        session.commit()


from sqlalchemy.orm import Session as Session


@pytest.fixture(scope="session")
def _base_url():
    return "http://testserver"


@pytest.fixture
def client(_seed_user):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _get_token(client) -> str:
    resp = client.post(
        "/api/v1/auth/token",
        json={"email": "test@2to-eos.local", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, f"Token request failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(client):
    token = _get_token(client)
    return {"Authorization": "Bearer " + token}
