from uuid import uuid4

from eos_v2.modules.industry.construction_real_estate import ConstructionRealEstatePack


def test_construction_pack_is_tenant_scoped_and_relationships_resolve():
    tenant = uuid4()
    pack = ConstructionRealEstatePack().build(tenant)
    assert pack.key == "construction-real-estate"
    assert pack.version == "1.0.0"
    assert len(pack.entities) == 5
    assert all(entity.tenant_id == tenant and entity.published is False for entity in pack.entities)
    ids = {entity.id for entity in pack.entities}
    for entity in pack.entities:
        for relationship in entity.relationships:
            assert relationship.target_entity_id in ids
