from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from eos_v2.application.identity.authentication import decode_access_token


class _SigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _StaticJWKClient:
    def __init__(self, key) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        return _SigningKey(self.key)


def _token(private_key, *, issuer: str = "https://identity.example.com/", audience: str = "eos-api") -> str:
    tenant_id = uuid4()
    actor_id = uuid4()
    claims = {
        "sub": "user-123",
        "tenant_id": str(tenant_id),
        "actor_id": str(actor_id),
        "iss": issuer,
        "aud": audience,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})
    return token, tenant_id, actor_id


def test_oidc_rs256_verifies_issuer_audience_and_identity_claims() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token, tenant_id, actor_id = _token(private_key)

    decoded_tenant, decoded_actor, subject = decode_access_token(
        token,
        "",
        auth_mode="oidc",
        oidc_issuer="https://identity.example.com/",
        oidc_audience="eos-api",
        oidc_jwks_client=_StaticJWKClient(private_key.public_key()),
    )

    assert decoded_tenant == tenant_id
    assert decoded_actor == actor_id
    assert subject == "user-123"


def test_oidc_rejects_wrong_issuer() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token, _, _ = _token(private_key, issuer="https://attacker.example.com/")

    with pytest.raises(ValueError, match="Invalid OIDC access token"):
        decode_access_token(
            token,
            "",
            auth_mode="oidc",
            oidc_issuer="https://identity.example.com/",
            oidc_audience="eos-api",
            oidc_jwks_client=_StaticJWKClient(private_key.public_key()),
        )


def test_oidc_rejects_wrong_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token, _, _ = _token(private_key, audience="another-api")

    with pytest.raises(ValueError, match="Invalid OIDC access token"):
        decode_access_token(
            token,
            "",
            auth_mode="oidc",
            oidc_issuer="https://identity.example.com/",
            oidc_audience="eos-api",
            oidc_jwks_client=_StaticJWKClient(private_key.public_key()),
        )
