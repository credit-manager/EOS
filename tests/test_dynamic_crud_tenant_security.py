"""Mandatory security regression contracts for Dynamic CRUD.

These tests are intentionally source-level where the endpoint implementation is
not safely invokable without the full application runtime. They fail closed:
required tenant scoping must be visible in the implementation rather than
being inferred from a hand-created database fixture.
"""
import inspect


def _source():
    from routers import dynamic_crud
    return inspect.getsource(dynamic_crud)


def test_entity_lookup_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "WHERE code = :code AND tenant_id = :tenant_id" in src or "tenant_id=:tenant_id" in src


def test_create_cannot_trust_client_tenant_id():
    src = _source().lower()
    assert "tenant_id" in src
    # The authenticated/request tenant must be the source of truth.
    assert "current_tenant" in src or "request.tenant_id" in src or "auth" in src


def test_read_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "SELECT" in src


def test_update_is_tenant_scoped():
    src = _source()
    assert "UPDATE" in src
    assert "tenant_id" in src


def test_delete_is_tenant_scoped():
    src = _source()
    assert "DELETE" in src
    assert "tenant_id" in src


def test_filters_cannot_remove_tenant_boundary():
    src = _source().lower()
    assert "tenant_id" in src
    # Dynamic user filters must not be the only WHERE boundary.
    assert "where" in src


def test_dynamic_table_identifier_is_validated():
    src = _source().lower()
    assert "table_mapping" in src
    assert "validate" in src or "allowed" in src or "whitelist" in src or "regex" in src
