"""Central tenant-scope authorization helpers.

Never trust a tenant_id supplied by a client when the authenticated user is
not a platform owner. Route handlers should call require_tenant_access before
using a path/query/body tenant identifier.
"""
from fastapi import HTTPException


def get_user_tenant_id(user: dict):
    return user.get("tenant_id") or user.get("tenantId")


def is_platform_owner(user: dict) -> bool:
    roles = user.get("roles") or user.get("role") or []
    if isinstance(roles, str):
        roles = [roles]
    role_names = {str(r).lower() for r in roles}
    return bool(
        user.get("is_platform_owner")
        or user.get("platform_owner")
        or "platform_owner" in role_names
        or "platform-owner" in role_names
        or "superadmin" in role_names
    )


def require_tenant_access(user: dict, tenant_id: str) -> str:
    """Return tenant_id only when the caller may operate on that tenant."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    if is_platform_owner(user):
        return tenant_id
    own_tenant = get_user_tenant_id(user)
    if not own_tenant or str(own_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Tenant access denied")
    return tenant_id


def require_owner_or_tenant(user: dict, tenant_id: str) -> str:
    """Alias kept intentionally small for route handlers."""
    return require_tenant_access(user, tenant_id)
