"""RBAC middleware — role-based access control for EOS."""
from enum import Enum
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .auth.security import decode_access_token


class Role(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"


# Prefixes that are platform-administration surfaces. The auth plane only
# issues {admin, member}; legacy tokens may carry manager/user/viewer.
# Fine-grained record/entity access is enforced downstream by the metadata
# permission layer (records/metadata/graph routers), NOT by coarse prefix RBAC.
_ADMIN_ONLY_PREFIXES = [
    "/api/v1/auth/members",
    "/api/v1/admin",
    "/api/v1/builder",
    "/api/v1/integrations",
    "/api/v1/marketplace",
    "/api/v1/sdk",
    "/api/v1/settings",
    "/api/v1/policy",
]

_OPERATIONAL_PREFIXES = [
    "/api/v1/financial",
    "/api/v1/construction",
    "/api/v1/retail",
    "/api/v1/manufacturing",
    "/api/v1/workflows",
    "/api/v1/documents",
    "/api/v1/analytics",
    "/api/v1/reporting",
    "/api/v1/ai",
    "/api/v1/notification",
    "/api/v1/globalization",
    "/api/v1/records",
    # Generic Records Runtime lives under /api/v1/entities/{code}/records;
    # entity-level access there is governed by metadata-driven permissions
    # in records/router.py, so the prefix must be member-reachable.
    "/api/v1/entities",
    "/api/v1/metadata",
    "/api/v1/lookup",
    "/api/v1/graph",
    "/api/v1/events",
    "/api/v1/rules",
]


# Permissions per role for route prefixes
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.ADMIN: ["*"],
    # Member: operational/business surface. Entity-level visibility and write
    # permissions are governed by metadata-driven permissions in the routers.
    Role.MEMBER: _OPERATIONAL_PREFIXES,
    # Legacy tokens (manager/user/viewer are no longer issued by the auth
    # plane but may exist in older deployments): manager keeps operational
    # surface plus reporting, without platform-administration prefixes.
    Role.MANAGER: _OPERATIONAL_PREFIXES + ["/api/v1/policy"],
    Role.USER: [
        "/api/v1/financial",
        "/api/v1/construction",
        "/api/v1/retail",
        "/api/v1/manufacturing",
        "/api/v1/workflows",
        "/api/v1/documents",
        "/api/v1/analytics",
        "/api/v1/records",
        "/api/v1/metadata",
        "/api/v1/lookup",
        "/api/v1/notification",
    ],
    Role.VIEWER: [
        "/api/v1/analytics",
        "/api/v1/reporting",
        "/api/v1/lookup",
        "/api/v1/records",
    ],
}

# Read-only roles cannot use write methods
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def has_permission(role: str, path: str, method: str) -> bool:
    """Check if a role has permission for a given path and method."""
    perms = ROLE_PERMISSIONS.get(role, [])
    if not perms:
        return False

    if "*" in perms:
        return True

    if role == Role.VIEWER and method in WRITE_METHODS:
        return False

    for prefix in perms:
        if path.startswith(prefix):
            return True

    return False


class RBACMiddleware(BaseHTTPMiddleware):
    """Enforces role-based access control on all API requests."""

    def __init__(self, app, excluded_paths: list[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/api/v1/auth",
            "/api/v1/health",
            "/api/v1/version",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if path.startswith("/ws/"):
            return await call_next(request)

        if any(path.startswith(p) for p in self.excluded_paths):
            return await call_next(request)

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header[7:]
        try:
            principal = decode_access_token(token)
            role = principal.role
        except Exception:
            return await call_next(request)
        if not has_permission(role, path, method):
            return JSONResponse(
                status_code=403,
                content={"detail": f"Role '{role}' lacks permission for {method} {path}"},
            )

        return await call_next(request)
