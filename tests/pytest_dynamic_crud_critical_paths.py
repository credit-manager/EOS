"""Executable unit coverage for Dynamic CRUD security boundaries."""
import pytest
from fastapi import HTTPException

import routers.dynamic_crud as dynamic_crud
from routers.dynamic_crud import (
    _junction_has_tenant_column,
    _require_tenant,
    _validate_identifier,
    list_records,
)


class Result:
    def __init__(self, rows=None, scalar_value=None):
        self.rows = rows or []
        self.scalar_value = scalar_value

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def scalar(self):
        return self.scalar_value

    def __iter__(self):
        return iter(self.rows)


class Row:
    def __init__(self, values, mapping):
        self.values = values
        self._mapping = mapping

    def __getitem__(self, index):
        return self.values[index]


class FakeDB:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return self.responses.pop(0)


class FakeQueryFilter:
    filters = []
    sorts = []
    limit = 100
    offset = 0


class FakeParser:
    def __init__(self, real_columns):
        self.real_columns = real_columns

    def parse_query(self, **kwargs):
        return FakeQueryFilter()

    def build_where_clause(self, filters):
        return "", {}

    def build_order_clause(self, sorts):
        return ""


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
    db = FakeDB([Result([(1,)])])
    assert _junction_has_tenant_column(db, 'user_roles') is True
    sql, params = db.calls[0]
    assert 'information_schema.columns' in sql
    assert params == {'table_name': 'user_roles'}


def test_dynamic_m2m_detects_unscoped_junction():
    db = FakeDB([Result([])])
    assert _junction_has_tenant_column(db, 'user_roles') is False


def test_dynamic_m2m_junction_identifier_is_validated():
    db = FakeDB([Result([])])
    with pytest.raises(HTTPException) as exc:
        _junction_has_tenant_column(db, 'user_roles;drop')
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_dynamic_m2m_route_scopes_target_and_junction_when_junction_has_tenant(monkeypatch):
    monkeypatch.setattr(dynamic_crud, 'QueryParser', FakeParser)
    db = FakeDB([
        Result([('entity-1', 'users', None)]),
        Result([('id',), ('tenant_id',), ('created_at',)]),
        Result(scalar_value=1),
        Result([Row(['u1'], {'id': 'u1', 'tenant_id': 'tenant-a', 'created_at': None})]),
        Result([('roles', 'many_to_many', 'id', 'id', None, True, 'user_roles', 'user_id', 'role_id')]),
        Result([('roles_table', 'tenant-a')]),
        Result([(1,)]),
        Result([Row(['r1', 'tenant-b'], {'id': 'r1', 'tenant_id': 'tenant-b'})]),
    ])
    response = await list_records(
        'users', include='roles', db=db, current_user={'id': 'u1', 'tenant_id': 'tenant-a'}
    )
    assert response['effective_tenant'] == 'tenant-a'
    m2m_sql, m2m_params = db.calls[-1]
    assert 't.tenant_id = :tid' in m2m_sql
    assert 'j.tenant_id = :tid' in m2m_sql
    assert m2m_params == {'sv': 'u1', 'tid': 'tenant-a'}


@pytest.mark.asyncio
async def test_dynamic_m2m_route_does_not_assume_junction_tenant_column(monkeypatch):
    monkeypatch.setattr(dynamic_crud, 'QueryParser', FakeParser)
    db = FakeDB([
        Result([('entity-1', 'users', None)]),
        Result([('id',), ('tenant_id',), ('created_at',)]),
        Result(scalar_value=1),
        Result([Row(['u1'], {'id': 'u1', 'tenant_id': 'tenant-a', 'created_at': None})]),
        Result([('roles', 'many_to_many', 'id', 'id', None, True, 'user_roles', 'user_id', 'role_id')]),
        Result([('roles_table', 'tenant-a')]),
        Result([]),
        Result([Row(['r1'], {'id': 'r1'})]),
    ])
    response = await list_records(
        'users', include='roles', db=db, current_user={'id': 'u1', 'tenant_id': 'tenant-a'}
    )
    assert response['count'] == 1
    m2m_sql, m2m_params = db.calls[-1]
    assert 't.tenant_id = :tid' in m2m_sql
    assert 'j.tenant_id = :tid' not in m2m_sql
    assert m2m_params == {'sv': 'u1', 'tid': 'tenant-a'}
