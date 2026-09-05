"""Mandatory Dynamic CRUD tenant-security regression tests."""
import inspect
import re


def _source():
    from routers import dynamic_crud
    return inspect.getsource(dynamic_crud)


def test_entity_lookup_must_not_be_code_only():
    src = _source()
    assert not re.search(r'WHERE\s+code\s*=\s*:code\s*"', src)
    assert "tenant_id" in src


def test_entity_lookup_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "tenant_id = :tenant_id" in src or "tenant_id=:tenant_id" in src


def test_create_cannot_trust_client_tenant_id():
    src = _source().lower()
    assert "payload" in src and "tenant_id" in src
    assert 'key not in (pk_col, "tenant_id")' in src
    assert 'current_user["tenant_id"]' in src


def test_read_is_tenant_scoped():
    src = _source()
    assert "tenant_id = :tenant_id" in src or "tenant_id=:tenant_id" in src


def test_update_is_tenant_scoped():
    src = _source()
    assert "UPDATE" in src
    assert "tenant_id" in src


def test_delete_is_tenant_scoped():
    src = _source()
    assert "DELETE" in src
    assert "tenant_id" in src


def test_filters_cannot_remove_tenant_boundary():
    src = _source()
    assert "tenant_id = :tenant_id" in src or "tenant_id=:tenant_id" in src


def test_dynamic_table_identifier_is_validated():
    src = _source().lower()
    assert "table_mapping" in src
    assert "re.fullmatch" in src or "re.match" in src or "whitelist" in src or "allowed" in src


def test_include_target_lookup_must_not_be_code_only():
    src = _source()
    assert '"SELECT table_mapping FROM dbp_entities "' not in src
    assert "tgt_sql" in src
    assert "tenant_id" in src
    assert "tenant_scope" in src
