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


def authorize(
    actor: Actor | None,
    tenant_id: UUID,
    permission: Permission,
    granted_permissions: frozenset[Permission] = frozenset(),
) -> AuthorizationDecision:
    """Authorize only active tenant members with an explicitly assigned permission."""
    if actor is None:
        return AuthorizationDecision(False, "authentication_required")
    if not actor.active:
        return AuthorizationDecision(False, "actor_inactive")
    if actor.tenant_id != tenant_id:
        return AuthorizationDecision(False, "tenant_mismatch")
    if permission not in granted_permissions:
        return AuthorizationDecision(False, f"permission_not_granted:{permission.value}")
    return AuthorizationDecision(True, "allowed")
