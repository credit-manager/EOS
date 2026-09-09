"""
EOS System — Tenant Identity Canonicalization

Single source of truth for tenant ID normalization and validation.
Every entry point (URL path, X-Tenant-ID header, JWT claims, DB values)
MUST pass through normalize_tenant_id() before comparison or storage.

Canonical form: lowercase; characters [a-z0-9_-]; non-empty.
"""
import re
from typing import Any, Optional

# Canonical tenant IDs: lowercase alphanumeric plus dash/underscore.
TENANT_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

# Reserved first path segments under /api/v1 that are NOT tenant-scoped
# routers (mounted without the /{tenant_id} prefix).
RESERVED_PATH_SEGMENTS = {"auth", "tenants", "users", "health", "docs", "openapi.json", "redoc"}

# Header carrying the caller-declared tenant context.
TENANT_HEADER = "X-Tenant-ID"


def is_valid_tenant_id(tenant_id: str) -> bool:
    """True if tenant_id is already in canonical form."""
    return bool(tenant_id) and bool(TENANT_ID_PATTERN.match(tenant_id))


def normalize_tenant_id(value: Any) -> Optional[str]:
    """Return the canonical (lowercase) form of a tenant ID, or None.

    None means "absent or invalid" — callers decide the HTTP policy
    (400 bad request vs 401 unauthenticated vs 403 forbidden).
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    if not candidate:
        return None
    if not TENANT_ID_PATTERN.match(candidate):
        return None
    return candidate
