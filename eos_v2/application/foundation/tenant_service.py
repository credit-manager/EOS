from __future__ import annotations

from typing import Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context


class TenantOwned(Protocol):
    tenant_id: UUID


def require_current_tenant(resource: TenantOwned) -> UUID:
    """Central guard for all foundation-module aggregates."""
    tenant_id = get_tenant_context().tenant_id
    if resource.tenant_id != tenant_id:
        raise PermissionError("Cross-tenant access denied")
    return tenant_id
