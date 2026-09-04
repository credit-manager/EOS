"""Regression tests for the SQLAlchemy tenant write boundary."""
import pytest
from database import _enforce_orm_tenant_boundary, current_tenant_id


class TenantObject:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id


class SessionLike:
    def __init__(self, new=(), dirty=()):
        self.new = list(new)
        self.dirty = list(dirty)


def test_tenant_context_rejects_cross_tenant_write():
    token = current_tenant_id.set("tenant-a")
    try:
        with pytest.raises(ValueError, match="Cross-tenant"):
            _enforce_orm_tenant_boundary(SessionLike(new=[TenantObject("tenant-b")]), None, None)
    finally:
        current_tenant_id.reset(token)


def test_missing_context_rejects_platform_default():
    token = current_tenant_id.set(None)
    try:
        with pytest.raises(ValueError, match="Tenant context"):
            _enforce_orm_tenant_boundary(SessionLike(new=[TenantObject("platform")]), None, None)
    finally:
        current_tenant_id.reset(token)


def test_matching_tenant_write_allowed():
    token = current_tenant_id.set("tenant-a")
    try:
        _enforce_orm_tenant_boundary(SessionLike(new=[TenantObject("tenant-a")]), None, None)
    finally:
        current_tenant_id.reset(token)
