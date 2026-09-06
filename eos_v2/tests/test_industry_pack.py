from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, tenant_context
from eos_v2.application.industry.pack_catalog import get_pack
from eos_v2.modules.industry.construction_real_estate import build_pack


def test_catalog_contains_construction_real_estate() -> None:
    pack = get_pack("construction-real-estate")
    assert pack.version == "1.0.0"
    assert pack.builder(uuid4()).key == "construction-real-estate"


def test_catalog_rejects_unknown_pack() -> None:
    with pytest.raises(KeyError, match="unknown-industry-pack"):
        get_pack("unknown-industry-pack")


def test_construction_pack_is_tenant_bound() -> None:
    tenant = uuid4()
    pack = build_pack(tenant)
    assert pack.tenant_id == tenant
    assert len(pack.entities) == 5
    assert {entity.name for entity in pack.entities} == {
        "land_parcel",
        "development_project",
        "property_unit",
        "property_contract",
        "construction_work_package",
    }
    for entity in pack.entities:
        assert entity.tenant_id == tenant


def test_pack_builder_cannot_change_tenant_context() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    with tenant_context(TenantContext(tenant_id=tenant_a, actor_id=uuid4())):
        pack = build_pack(tenant_b)
        assert pack.tenant_id == tenant_b
