"""
EOS System — Tenant Middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Optional

from app.core.config import settings
from app.core.tenancy import (
    RESERVED_PATH_SEGMENTS,
    TENANT_HEADER,
    is_valid_tenant_id,
    normalize_tenant_id,
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and normalize tenant ID from requests.

    Multi-tenancy Strategy:
    - Row-Level tenant_id columns (shared schema)
    - URL Path: /api/v1/{tenant_id}/... for business routers
    - Header: X-Tenant-ID
    - JWT claim: tenant_id

    Normalization contract:
    - Every extracted value passes through core.tenancy.normalize_tenant_id()
      so path/header/JWT comparisons always operate on the canonical form.
    - request.state.tenant_source records where the value came from:
      "path", "header", or absent when no tenant context was provided.
    """

    # Routes that never carry tenant context.
    SKIP_PATHS = {
        "/health",
        "/api/v1/health",
        "/",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip tenant extraction for health checks and docs
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Extract raw candidates from URL path and header independently.
        raw_path_tenant, raw_header_tenant = self._extract_tenant_candidates(request)

        # Canonicalize both; None means absent-or-invalid per candidate.
        path_tenant = normalize_tenant_id(raw_path_tenant)
        header_tenant = normalize_tenant_id(raw_header_tenant)

        # Both contexts supplied: they must agree after normalization.
        # A contradiction is treated as a cross-tenant access attempt.
        if raw_path_tenant is not None and raw_header_tenant is not None:
            if path_tenant is None or header_tenant is None:
                return Response(
                    content='{"error": "Invalid tenant ID format"}',
                    status_code=400,
                    media_type="application/json",
                )
            if path_tenant != header_tenant:
                return Response(
                    content='{"error": "Conflicting tenant identifiers"}',
                    status_code=403,
                    media_type="application/json",
                )

        raw_tenant_id = raw_path_tenant if raw_path_tenant is not None else raw_header_tenant
        tenant_id = path_tenant if raw_path_tenant is not None else header_tenant
        source = "path" if raw_path_tenant is not None else "header"

        if not tenant_id:
            # Allow unauthenticated routes (login, register, etc.)
            if self._is_public_route(request.url.path):
                return await call_next(request)

            # Authenticated routes on non-tenant-scoped routers (/auth/*,
            # /users/*, /tenants/*) rely on the JWT alone — let them through;
            # get_current_user enforces the tenant claim there.
            if self._is_reserved_segment_path(request.url.path):
                return await call_next(request)

            if raw_tenant_id is not None:
                return Response(
                    content='{"error": "Invalid tenant ID format"}',
                    status_code=400,
                    media_type="application/json",
                )

            return Response(
                content='{"error": "Tenant ID required"}',
                status_code=400,
                media_type="application/json",
            )

        # Defense in depth: normalizer already guarantees this shape.
        if not is_valid_tenant_id(tenant_id):
            return Response(
                content='{"error": "Invalid tenant ID format"}',
                status_code=400,
                media_type="application/json",
            )

        # Store canonical tenant ID + provenance in request state so the
        # security layer can enforce JWT/request consistency.
        request.state.tenant_id = tenant_id
        request.state.tenant_source = source

        # Process request
        response = await call_next(request)

        # Add tenant header to response
        response.headers["X-Tenant-ID"] = tenant_id

        return response

    def _extract_tenant_candidates(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """Return (raw_path_candidate, raw_header_candidate).

        Reserved segments (auth/tenants/users) are NOT tenant-scoped, so a
        match on them yields no path candidate instead of misreading
        e.g. /api/v1/auth/me as tenant "auth".
        """
        # Candidate 1: From URL path (/api/v1/{tenant_id}/...)
        path_candidate: Optional[str] = None
        path_parts = request.url.path.strip("/").split("/")
        if (
            len(path_parts) >= 4
            and path_parts[0] == "api"
            and path_parts[1] == "v1"
            and path_parts[2] not in RESERVED_PATH_SEGMENTS
        ):
            path_candidate = path_parts[2]

        # Candidate 2: From header
        return path_candidate, request.headers.get(TENANT_HEADER)

    def _is_public_route(self, path: str) -> bool:
        """Check if the route is public (no tenant required)."""
        public_routes = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/tenants",
            "/api/v1/health",
        ]
        return path in public_routes

    def _is_reserved_segment_path(self, path: str) -> bool:
        """True for routes on routers mounted WITHOUT /{tenant_id} prefix.

        These endpoints authenticate via JWT only; the second path segment
        after v1 is a router name, never a tenant ID.
        """
        parts = path.strip("/").split("/")
        return (
            len(parts) >= 3
            and parts[0] == "api"
            and parts[1] == "v1"
            and parts[2] in RESERVED_PATH_SEGMENTS
        )
