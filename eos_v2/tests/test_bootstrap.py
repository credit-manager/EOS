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


def test_production_requires_oidc():
    settings = Settings(
        environment="production",
        database_url="postgresql://user:pass@localhost/db",
        secret_key="x" * 32,
        allowed_hosts=("erp.example.com",),
        cors_origins=("https://erp.example.com",),
        metrics_token="m" * 32,
        auth_mode="hs256",
    )
    with pytest.raises(ValueError, match="EOS_AUTH_MODE must be oidc"):
        settings.validate()


def test_production_accepts_valid_oidc_contract():
    settings = Settings(
        environment="production",
        database_url="postgresql://user:pass@localhost/db",
        allowed_hosts=("erp.example.com",),
        cors_origins=("https://erp.example.com",),
        metrics_token="m" * 32,
        auth_mode="oidc",
        oidc_issuer="https://identity.example.com/",
        oidc_audience="eos-api",
        oidc_jwks_url="https://identity.example.com/.well-known/jwks.json",
    )
    settings.validate()


def test_tenant_context_is_explicit_and_scoped():
    tenant_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id=tenant_id))
    try:
        assert get_tenant_context().tenant_id == tenant_id
    finally:
        reset_tenant_context(token)
    with pytest.raises(RuntimeError, match="Tenant context is required"):
        get_tenant_context()


def test_rejected_request_is_audited_without_sensitive_headers(caplog):
    app = create_app(Settings(environment="test"))
    client = TestClient(app)
    with caplog.at_level("WARNING", logger="eos.security"):
        response = client.get("/api/v1/auth/me", headers={"X-Request-ID": "audit-test-id"})
    assert response.status_code == 401
    assert "security_event event=request_rejected" in caplog.text
    assert "audit-test-id" in caplog.text
    assert "Authorization" not in caplog.text
