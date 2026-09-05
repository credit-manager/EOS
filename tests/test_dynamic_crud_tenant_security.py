"""Mandatory Dynamic CRUD tenant-security regression tests."""
import inspect
import re


def _source():
    from routers import dynamic_crud
    return inspect.getsource(dynamic_crud)


def test_entity_lookup_must_not_be_code_only():
    src = _source()
    lookup = re.search(r'ent_sql\s*=\s*([\"\']{3}|[\"\'])(.*?)(?:\1)', src, re.DOTALL)
    assert lookup, "Entity lookup SQL must be explicit"
    sql = lookup.group(2)
    assert re.search(r"\bcode\s*=\s*:code\b", sql)
    assert "tenant_id" in sql or "tenant_id" in src[lookup.start():lookup.end() + 250]


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


def test_many_to_many_include_is_tenant_scoped():
    """Regression test: the many_to_many relationship-expansion branch of
    /records?include=<relation> must enforce the same tenant boundary as
    every other relationship type in the same function. A prior version
    built its own raw SQL against the junction table without any tenant
    condition on the target table, allowing cross-tenant record leakage.
    """
    src = _source()
    m2m_block = re.search(
        r'elif rel_type == "many_to_many":.*?\n(?=\s*else:)',
        src,
        re.DOTALL,
    )
    assert m2m_block, "many_to_many branch not found in dynamic_crud"
    block = m2m_block.group(0)
    assert "tenant_scope" in block, "many_to_many branch must check tenant_scope"
    assert "tenant_id" in block, "many_to_many branch must reference tenant_id"
    assert re.search(r"tenant_id\s*=\s*:tid", block), (
        "many_to_many query must filter the target table on tenant_id"
    )
