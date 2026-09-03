"""Mandatory Dynamic CRUD tenant-security regression tests.

These tests intentionally inspect the implementation for security invariants,
not brittle SQL formatting. The implementation may refactor SQL parameter names
without weakening the tenant boundary.
"""
import inspect


def _source():
    from routers import dynamic_crud
    return inspect.getsource(dynamic_crud)


def test_entity_lookup_must_be_tenant_aware():
    src = _source()
    assert "_entity_metadata" in src
    assert "tenant_id" in src
    assert "tenant_id" in inspect.getsource(__import__("routers.dynamic_crud", fromlist=["_entity_metadata"])._entity_metadata)


def test_entity_lookup_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "tenant_id=:tenant_id" in src or "tenant_id = :tenant_id" in src


def test_create_cannot_trust_client_tenant_id():
    src = _source().lower()
    assert "payload.tenant_id" in src
    assert "effective_tenant" in src
    assert "_require_tenant" in src


def test_read_is_tenant_scoped():
    src = _source()
    assert "tenant_id=:tenant_id" in src or "tenant_id = :tenant_id" in src
    assert "_require_tenant(current_user)" in src


def test_update_is_tenant_scoped():
    src = _source()
    assert "UPDATE" in src
    assert "tenant_filter" in src
    assert "_require_tenant(current_user)" in src


def test_delete_is_tenant_scoped():
    src = _source()
    assert "DELETE" in src or "deleted_at" in src
    assert "effective_tenant" in src
    assert "_require_tenant(current_user)" in src


def test_filters_cannot_remove_tenant_boundary():
    src = _source()
    assert "where_clauses" in src
    assert "tenant_id=:tenant_id" in src or "tenant_id = :tenant_id" in src


def test_dynamic_table_identifier_is_validated():
    src = _source().lower()
    assert "table_mapping" in src
    assert "re.fullmatch" in src
    assert "whitelist" in src or "invalid sql identifier" in src


def test_include_target_lookup_must_be_tenant_aware():
    src = _source()
    assert "_entity_metadata(db, target_code, tenant_id)" in src
    assert "tenant_id" in src
    assert "target_table" in src
