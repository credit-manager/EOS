from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from jwt import PyJWKClient

from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import Permission
from eos_v2.domain.tenancy.entities import Tenant


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    actor: Actor
    tenant: Tenant
    permissions: frozenset[Permission]


def decode_access_token(
    token: str,
    secret_key: str,
    *,
    auth_mode: str = "hs256",
    oidc_issuer: str = "",
    oidc_audience: str = "",
    oidc_jwks_client: PyJWKClient | None = None,
) -> tuple[UUID, UUID, str]:
    if auth_mode == "oidc":
        if not oidc_issuer or not oidc_audience or oidc_jwks_client is None:
            raise ValueError("OIDC authentication is not configured")
        try:
            signing_key = oidc_jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=oidc_audience,
                issuer=oidc_issuer,
                options={"require": ["exp", "sub", "tenant_id", "actor_id"]},
            )
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid OIDC access token") from exc
    else:
        if not secret_key:
            raise ValueError("Authentication secret is not configured")
        try:
            claims = jwt.decode(
                token,
                secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "tenant_id", "actor_id"]},
            )
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid access token") from exc

    try:
        tenant_id = UUID(str(claims["tenant_id"]))
        actor_id = UUID(str(claims["actor_id"]))
        subject = str(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid access token claims") from exc
    if not subject:
        raise ValueError("Invalid access token subject")
    return tenant_id, actor_id, subject
