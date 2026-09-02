"""Central tenant-scope authorization helpers.

The effective tenant comes from authenticated identity. Client-supplied tenant
IDs are accepted only after explicit membership/owner authorization.
"""
from fastapi import HTTPException


def get_user_tenant_id(user: dict):
    return user.get("tenant_id") or user.get("tenantId")


def is_platform_owner(user: dict) -> bool:
    """Only the explicit platform-owner claim/role may cross tenant boundaries."""
    roles = user.get("roles") or user.get("role") or []
    if isinstance(roles, str):
        roles = [roles]
    role_names = {str(r).lower() for r in roles}
    return bool(user.get("is_platform_owner") is True or "platform_owner" in role_names)


def require_tenant_access(user: dict, tenant_id: str) -> str:
    """Return a normalized tenant ID only when the caller may access it."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    requested = str(tenant_id).strip().lower()
    if is_platform_owner(user):
        return requested
    own_tenant = get_user_tenant_id(user)
    if not own_tenant or str(own_tenant).strip().lower() != requested:
        raise HTTPException(status_code=403, detail="Tenant access denied")
    return requested


def require_owner_or_tenant(user: dict, tenant_id: str) -> str:
    return require_tenant_access(user, tenant_id)
