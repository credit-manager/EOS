from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from eos_v2.app import create_app
from eos_v2.app.config import Settings
from eos_v2.app.tenant_context import TenantContext, get_tenant_context, reset_tenant_context, set_tenant_context


def test_app_boots_and_exposes_liveness():
    app = create_app(Settings(environment="test"))
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/").json()["runtime"] == "v2"


def test_production_requires_database():
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_app(Settings(environment="production", secret_key="x" * 32))


def test_tenant_context_is_explicit_and_scoped():
    tenant_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id=tenant_id))
    try:
        assert get_tenant_context().tenant_id == tenant_id
    finally:
        reset_tenant_context(token)
    with pytest.raises(RuntimeError, match="Tenant context is required"):
        get_tenant_context()
