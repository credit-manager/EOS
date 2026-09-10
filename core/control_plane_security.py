"""Security guards for privileged platform-control operations."""
from __future__ import annotations

from fastapi import HTTPException, Request


_MIN_ADMIN_PASSWORD_LENGTH = 12


async def validate_tenant_provisioning_request(request: Request) -> None:
    """Reject insecure tenant-admin provisioning before the legacy handler runs."""
    if request.method.upper() != "POST" or request.url.path.rstrip("/") != "/api/v1/control/tenants":
        return

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON request body") from exc

    password = body.get("admin_password") if isinstance(body, dict) else None
    if not isinstance(password, str) or len(password) < _MIN_ADMIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"admin_password must be at least {_MIN_ADMIN_PASSWORD_LENGTH} characters",
        )
