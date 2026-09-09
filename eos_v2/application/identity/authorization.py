from __future__ import annotations

from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import AuthorizationDecision, Permission, authorize


def authorize_current_actor(
    actor: Actor | None,
    permission: Permission,
    granted_permissions: frozenset[Permission] = frozenset(),
) -> AuthorizationDecision:
    """Authorize against the request-scoped tenant, never a caller-supplied tenant value."""
    context = get_tenant_context()
    return authorize(actor, context.tenant_id, permission, granted_permissions)


def require_tenant_match(actor: Actor, resource_tenant_id: UUID) -> None:
    """Fail closed when a resource belongs to another tenant."""
    context = get_tenant_context()
    if actor.tenant_id != context.tenant_id or resource_tenant_id != context.tenant_id:
        raise PermissionError("Cross-tenant access denied")
