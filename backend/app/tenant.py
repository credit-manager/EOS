from uuid import UUID

from fastapi import Header, HTTPException


async def require_tenant(x_tenant_id: str | None = Header(default=None)) -> UUID:
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="X-Tenant-ID is required")
    try:
        return UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid tenant id") from exc
