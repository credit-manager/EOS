from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt

from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import Permission
from eos_v2.domain.tenancy.entities import Tenant


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    actor: Actor
    tenant: Tenant
    permissions: frozenset[Permission]


def decode_access_token(token: str, secret_key: str) -> tuple[UUID, UUID, str]:
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
