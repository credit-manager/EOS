from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from eos_v2.domain.identity.entities import Actor


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def authorize(actor: Actor | None, tenant_id: UUID, permission: Permission) -> AuthorizationDecision:
    """Deny by default; an actor may only act inside its authenticated tenant."""
    if actor is None:
        return AuthorizationDecision(False, "authentication_required")
    if not actor.active:
        return AuthorizationDecision(False, "actor_inactive")
    if actor.tenant_id != tenant_id:
        return AuthorizationDecision(False, "tenant_mismatch")
    # Role/permission assignment will be introduced by the identity persistence slice.
    # Until then, authenticated tenant membership alone never grants privileged access.
    return AuthorizationDecision(False, f"permission_not_granted:{permission.value}")
