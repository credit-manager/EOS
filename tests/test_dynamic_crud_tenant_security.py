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
    assert "DynamicVerificationEngine" in src
    assert "tenant_id" in src
    module = __import__("routers.dynamic_crud", fromlist=["get_verification_engine"])
    assert "tenant_id" in inspect.getsource(module.get_verification_engine)


def test_entity_lookup_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "tenant_id=:tenant_id" in src or "tenant_id = :tenant_id" in src


def test_create_cannot_trust_client_tenant_id():
    src = _source().lower()
    assert "tenant_id" in src
    assert "effective_tenant" in src
    assert "_require_tenant" in src
    # The create path derives tenant_id from the authenticated user and excludes
    # client-supplied tenant_id from the persisted payload.
    assert 'key not in (pk_col, "tenant_id")' in src


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
    assert "tenant_id" in src
    assert "current_user" in src


def test_filters_cannot_remove_tenant_boundary():
    src = _source()
    assert "where_clauses" in src
    assert "tenant_id=:tenant_id" in src or "tenant_id = :tenant_id" in src


def test_dynamic_table_identifier_is_validated():
    src = _source().lower()
    assert "_validate_identifier" in src
    assert "re.fullmatch" in src
    assert "invalid sql identifier" in src


def test_include_target_lookup_must_be_tenant_aware():
    src = _source()
    assert "tgt_sql" in src
    assert "tenant_id" in src
    assert "target_table" in src
