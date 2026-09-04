"""Executable unit coverage for Dynamic CRUD security boundaries."""
import pytest
from fastapi import HTTPException

from routers.dynamic_crud import (
    _junction_has_tenant_column,
    _require_tenant,
    _validate_identifier,
)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return Result(self.rows)


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
    "users' OR '1'='1", '', None,
])
def test_dynamic_identifier_rejects_unsafe_sql_identifiers(identifier):
    with pytest.raises(HTTPException) as exc:
        _validate_identifier(identifier)
    assert exc.value.status_code == 400


def test_dynamic_m2m_detects_tenant_scoped_junction():
    db = FakeDB([(1,)])
    assert _junction_has_tenant_column(db, 'user_roles') is True
    sql, params = db.calls[0]
    assert 'information_schema.columns' in sql
    assert params == {'table_name': 'user_roles'}


def test_dynamic_m2m_detects_unscoped_junction():
    db = FakeDB([])
    assert _junction_has_tenant_column(db, 'user_roles') is False


def test_dynamic_m2m_junction_identifier_is_validated():
    db = FakeDB([])
    with pytest.raises(HTTPException) as exc:
        _junction_has_tenant_column(db, 'user_roles;drop')
    assert exc.value.status_code == 400
