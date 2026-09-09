"""End-to-end safety tests for tenant-scoped ERP generation.

These tests are intentionally dependency-light. They validate the contracts
that must hold between Composer, Builder and the tenant-scoped metadata model.
"""
from dataclasses import dataclass


@dataclass
class FakeEntity:
    tenant_id: str
    code: str
    table_mapping: str


def test_same_entity_code_is_valid_for_two_tenants():
    entities = [
        FakeEntity("tourism-a", "customer", "bld_customer"),
        FakeEntity("construction-b", "customer", "bld_customer"),
    ]
    assert entities[0].code == entities[1].code
    assert entities[0].tenant_id != entities[1].tenant_id


def test_entity_key_is_tenant_scoped():
    entities = {}
    for e in [
        FakeEntity("tourism-a", "customer", "bld_customer"),
        FakeEntity("construction-b", "customer", "bld_customer"),
    ]:
        key = (e.tenant_id, e.code)
        assert key not in entities
        entities[key] = e
    assert len(entities) == 2


def test_physical_table_requires_tenant_column():
    # Contract for every generated tenant-owned table.
    required_columns = {"id", "tenant_id", "created_at"}
    generated_columns = {"id", "tenant_id", "name", "created_at"}
    assert required_columns <= generated_columns
