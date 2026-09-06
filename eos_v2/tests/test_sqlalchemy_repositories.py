from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.records.service import DynamicRecordService
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.domain.metadata.records import DynamicRecord
from eos_v2.infrastructure.db.metadata_models import Base, MetadataEntityModel
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.infrastructure.db.record_models import DynamicRecordModel, DynamicRecordUniqueValueModel, RecordBase
from eos_v2.infrastructure.db.record_repository import SqlAlchemyRecordRepository, UniqueValueConflict


def test_metadata_repository_is_tenant_scoped() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_a, tenant_b = uuid4(), uuid4()
    definition = EntityDefinition(tenant_id=tenant_a, name="customer", published=True)
    with Session(engine) as session:
        token = set_tenant_context(TenantContext(tenant_a, uuid4()))
        try:
            SqlAlchemyMetadataRepository(session).add(definition)
            session.commit()
        finally:
            reset_tenant_context(token)
        token = set_tenant_context(TenantContext(tenant_b, uuid4()))
        try:
            with pytest.raises(KeyError):
                SqlAlchemyMetadataRepository(session).get(definition.id)
        finally:
            reset_tenant_context(token)


def test_record_repository_round_trips_typed_values_and_enforces_unique() -> None:
    engine = create_engine("sqlite:///:memory:")
    RecordBase.metadata.create_all(engine)
    tenant = uuid4()
    entity = uuid4()
    record = DynamicRecord(
        tenant_id=tenant,
        entity_id=entity,
        entity_version=1,
        data={
            "code": "C-001",
            "amount": Decimal("12.50"),
            "when": datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc),
            "day": date(2026, 9, 6),
            "ref": uuid4(),
        },
    )
    with Session(engine) as session:
        token = set_tenant_context(TenantContext(tenant, uuid4()))
        try:
            repo = SqlAlchemyRecordRepository(session)
            repo.add(record, {"code": "C-001"})
            session.commit()
            loaded = repo.get(record.id)
            assert loaded.data == record.data
            duplicate = DynamicRecord(tenant_id=tenant, entity_id=entity, entity_version=1, data={"code": "C-001"})
            with pytest.raises(UniqueValueConflict):
                repo.add(duplicate, {"code": "C-001"})
        finally:
            reset_tenant_context(token)


def test_record_repository_cannot_cross_tenant() -> None:
    engine = create_engine("sqlite:///:memory:")
    RecordBase.metadata.create_all(engine)
    tenant_a, tenant_b = uuid4(), uuid4()
    record = DynamicRecord(tenant_id=tenant_a, entity_id=uuid4(), entity_version=1, data={"name": "Acme"})
    with Session(engine) as session:
        token = set_tenant_context(TenantContext(tenant_a, uuid4()))
        try:
            SqlAlchemyRecordRepository(session).add(record)
            session.commit()
        finally:
            reset_tenant_context(token)
        token = set_tenant_context(TenantContext(tenant_b, uuid4()))
        try:
            with pytest.raises(KeyError):
                SqlAlchemyRecordRepository(session).get(record.id)
        finally:
            reset_tenant_context(token)


def test_relationship_integrity_uses_target_entity_and_tenant() -> None:
    engine = create_engine("sqlite:///:memory:")
    RecordBase.metadata.create_all(engine)
    tenant = uuid4()
    target_entity, source_entity = uuid4(), uuid4()
    target = DynamicRecord(tenant_id=tenant, entity_id=target_entity, entity_version=1, data={})
    source_definition = EntityDefinition(
        id=source_entity,
        tenant_id=tenant,
        name="order",
        relationships=(RelationshipDefinition("customer", target_entity, required=True),),
        published=True,
    )
    with Session(engine) as session:
        token = set_tenant_context(TenantContext(tenant, uuid4()))
        try:
            repo = SqlAlchemyRecordRepository(session)
            repo.add(target)
            session.commit()
            service = DynamicRecordService(repo)
            source = service.create(source_definition, {"customer": target.id})
            assert source.data["customer"] == target.id
        finally:
            reset_tenant_context(token)
