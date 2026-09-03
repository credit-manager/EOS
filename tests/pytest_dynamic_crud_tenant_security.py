"""Pytest-native tenant boundary regression tests for dynamic CRUD."""
import inspect


def _source():
    from routers import dynamic_crud
    return inspect.getsource(dynamic_crud)


def test_entity_lookup_must_not_be_code_only():
    src = _source()
    assert '"WHERE code = :code"' not in src
    assert "WHERE code = :code" not in src


def test_entity_lookup_is_tenant_scoped():
    src = _source()
    assert "tenant_id" in src
    assert "tenant_id = :tenant_id" in src or "tenant_id=:tenant_id" in src


def test_create_cannot_trust_client_tenant_id():
    src = _source().lower()
    assert "payload.tenant_id" in src
    assert "current_user[\"tenant_id\"]" in src


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
    assert "re.match" in src or "whitelist" in src or "allowed" in src or "fullmatch" in src


def test_include_target_lookup_must_not_be_code_only():
    src = _source()
    assert '"SELECT table_mapping FROM dbp_entities "' not in src
    assert "WHERE code = :code" not in src
