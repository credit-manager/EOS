from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.metadata.service import MetadataService
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition


def test_entity_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValueError, match="Field names must be unique"):
        EntityDefinition(
            name="customer",
            fields=(
                FieldDefinition("name", FieldType.TEXT),
                FieldDefinition("name", FieldType.TEXT),
            ),
        )


def test_entity_rejects_duplicate_relationship_names() -> None:
    with pytest.raises(ValueError, match="Relationship names must be unique"):
        EntityDefinition(
            name="order",
            relationships=(
                RelationshipDefinition("customer", uuid4()),
                RelationshipDefinition("customer", uuid4()),
            ),
        )


def test_metadata_publish_requires_authenticated_tenant_match() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    definition = EntityDefinition(name="customer", tenant_id=tenant_b)
    token = set_tenant_context(TenantContext(tenant_a, uuid4()))
    try:
        with pytest.raises(PermissionError, match="does not match"):
            MetadataService().publish(definition)
    finally:
        reset_tenant_context(token)


def test_metadata_get_is_tenant_scoped() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    definition = EntityDefinition(name="customer", tenant_id=tenant_a)
    service = MetadataService()
    token_a = set_tenant_context(TenantContext(tenant_a, uuid4()))
    try:
        published = service.publish(definition)
    finally:
        reset_tenant_context(token_a)

    token_b = set_tenant_context(TenantContext(tenant_b, uuid4()))
    try:
        with pytest.raises(KeyError, match="not found"):
            service.get(published.id)
    finally:
        reset_tenant_context(token_b)
