"""Executable unit coverage for Dynamic CRUD security boundaries."""
import pytest
from fastapi import HTTPException

from routers.dynamic_crud import _require_tenant, _validate_identifier


def test_dynamic_crud_requires_authenticated_tenant():
    with pytest.raises(HTTPException) as exc:
        _require_tenant(None)
    assert exc.value.status_code == 401


def test_dynamic_crud_rejects_authenticated_user_without_tenant():
    with pytest.raises(HTTPException) as exc:
        _require_tenant({'id': 'u1', 'roles': ['user']})
    assert exc.value.status_code == 401


def test_dynamic_crud_uses_authenticated_tenant():
    assert _require_tenant({'id': 'u1', 'tenant_id': 'tenant-a'}) == 'tenant-a'


@pytest.mark.parametrize('identifier', [
    'users', 'sales_orders', 'tenant_123',
])
def test_dynamic_identifier_accepts_safe_sql_identifiers(identifier):
    assert _validate_identifier(identifier) == identifier


@pytest.mark.parametrize('identifier', [
    'users;', 'users--', 'users drop', 'users.table', 'DROP TABLE users',
    'users\' OR \'1\'=\'1', '', None,
])
def test_dynamic_identifier_rejects_unsafe_sql_identifiers(identifier):
    with pytest.raises(HTTPException) as exc:
        _validate_identifier(identifier)
    assert exc.value.status_code == 400
