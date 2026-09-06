from __future__ import annotations

from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.records.service import DynamicRecordService, InMemoryRecordRepository
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition


def context(tenant_id):
    return set_tenant_context(TenantContext(tenant_id, uuid4()))


def test_unique_field_is_enforced_within_tenant_and_entity() -> None:
    tenant = uuid4()
    definition = EntityDefinition(
        tenant_id=tenant,
        name="customer",
        fields=(FieldDefinition("code", FieldType.TEXT, required=True, unique=True),),
        published=True,
    )
    repo = InMemoryRecordRepository()
    service = DynamicRecordService(repo)
    token = context(tenant)
    try:
        service.create(definition, {"code": "C-001"})
        with pytest.raises(ValueError, match="Unique field"):
            service.create(definition, {"code": "C-001"})
    finally:
        reset_tenant_context(token)


def test_same_unique_value_is_allowed_for_another_tenant() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    definition_a = EntityDefinition(tenant_id=tenant_a, name="customer", fields=(FieldDefinition("code", FieldType.TEXT, unique=True),), published=True)
    definition_b = EntityDefinition(id=definition_a.id, tenant_id=tenant_b, name="customer", fields=definition_a.fields, published=True)
    repo = InMemoryRecordRepository()
    service = DynamicRecordService(repo)

    token_a = context(tenant_a)
    try:
        service.create(definition_a, {"code": "C-001"})
    finally:
        reset_tenant_context(token_a)
    token_b = context(tenant_b)
    try:
        service.create(definition_b, {"code": "C-001"})
    finally:
        reset_tenant_context(token_b)


def test_relationship_requires_target_in_same_tenant_and_entity() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    target = EntityDefinition(tenant_id=tenant_a, name="customer", published=True)
    source = EntityDefinition(
        tenant_id=tenant_a,
        name="order",
        relationships=(RelationshipDefinition("customer", target.id, required=True),),
        published=True,
    )
    repo = InMemoryRecordRepository()
    service = DynamicRecordService(repo)

    token = context(tenant_a)
    try:
        with pytest.raises(ValueError, match="Relationship target not found"):
            service.create(source, {"customer": uuid4()})
        customer = service.create(target, {})
        order = service.create(source, {"customer": customer.id})
        assert order.data["customer"] == customer.id
    finally:
        reset_tenant_context(token)

    token = context(tenant_b)
    try:
        with pytest.raises(ValueError, match="Relationship target not found"):
            service.create(source, {"customer": customer.id})
    finally:
        reset_tenant_context(token)


def test_stale_write_is_rejected() -> None:
    tenant = uuid4()
    definition = EntityDefinition(tenant_id=tenant, name="customer", fields=(FieldDefinition("name", FieldType.TEXT, required=True),), published=True)
    repo = InMemoryRecordRepository()
    service = DynamicRecordService(repo)
    token = context(tenant)
    try:
        record = service.create(definition, {"name": "Acme"})
        updated = service.update(definition, record.id, {"name": "Acme Ltd"}, expected_row_version=1)
        assert updated.row_version == 2
        with pytest.raises(RuntimeError, match="Stale"):
            service.update(definition, record.id, {"name": "Stale"}, expected_row_version=1)
    finally:
        reset_tenant_context(token)
