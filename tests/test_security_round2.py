import asyncio

import jwt
import pytest

from core.auth import _designated_platform_owners, require_admin_role
from core.production_auth import create_access_token, verify_token


def test_platform_owner_has_no_implicit_default(monkeypatch):
    monkeypatch.delenv("EOS_PLATFORM_OWNER_EMAILS", raising=False)
    assert _designated_platform_owners() == set()


def test_manager_is_not_tenant_admin():
    with pytest.raises(Exception) as exc:
        asyncio.run(require_admin_role({"id": "u1", "roles": ["dynamic_manager"]}))
    assert getattr(exc.value, "status_code", None) == 403


def test_admin_is_tenant_admin():
    user = asyncio.run(require_admin_role({"id": "u1", "roles": ["admin"]}))
    assert user["id"] == "u1"


def test_production_jwt_requires_trust_claims(monkeypatch):
    monkeypatch.setenv("EOS_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("EOS_JWT_ISSUER", "eos-test")
    monkeypatch.setenv("EOS_JWT_AUDIENCE", "eos-api-test")
    token = create_access_token("u1", extra_data={"tenant_id": "t1", "roles": ["admin"], "email": "u@example.com"})
    payload = verify_token(token)
    assert payload["sub"] == "u1"
    assert payload["iss"] == "eos-test"
    assert payload["aud"] == "eos-api-test"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_production_jwt_reserves_trust_claims(monkeypatch):
    monkeypatch.setenv("EOS_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("EOS_JWT_ISSUER", "eos-test")
    monkeypatch.setenv("EOS_JWT_AUDIENCE", "eos-api-test")
    token = create_access_token("u1", extra_data={"iss": "attacker", "aud": "attacker", "type": "refresh", "jti": "attacker"})
    payload = verify_token(token)
    assert payload["iss"] == "eos-test"
    assert payload["aud"] == "eos-api-test"
    assert payload["type"] == "access"
    assert payload["jti"] != "attacker"


def test_production_jwt_rejects_wrong_audience(monkeypatch):
    monkeypatch.setenv("EOS_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("EOS_JWT_ISSUER", "eos-test")
    monkeypatch.setenv("EOS_JWT_AUDIENCE", "eos-api-test")
    token = jwt.encode(
        {"sub": "u1", "iat": 1_000_000_000, "exp": 4_000_000_000, "iss": "eos-test", "aud": "wrong", "type": "access", "jti": "j1"},
        "x" * 64,
        algorithm="HS256",
    )
    with pytest.raises(Exception) as exc:
        verify_token(token)
    assert getattr(exc.value, "status_code", None) == 401
