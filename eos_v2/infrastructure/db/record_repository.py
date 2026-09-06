from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.records import DynamicRecord
from eos_v2.domain.metadata.serialization import canonical_value, from_storage, to_storage
from eos_v2.infrastructure.db.record_models import DynamicRecordModel, DynamicRecordUniqueValueModel


class UniqueValueConflict(ValueError):
    """Raised when a metadata-defined unique field already exists in the tenant."""


class SqlAlchemyRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: DynamicRecord, unique_values: dict[str, Any] | None = None) -> None:
        tenant_id = get_tenant_context().tenant_id
        if record.tenant_id != tenant_id:
            raise PermissionError("Record tenant does not match current tenant")
        self.session.add(DynamicRecordModel(
            id=record.id, tenant_id=tenant_id, entity_id=record.entity_id,
            entity_version=record.entity_version, data=to_storage(record.data),
            row_version=record.row_version, created_at=record.created_at,
            updated_at=record.updated_at,
        ))
        for field_name, value in (unique_values or {}).items():
            if value is None:
                continue
            self.session.add(DynamicRecordUniqueValueModel(
                tenant_id=tenant_id, entity_id=record.entity_id,
                field_name=field_name, value_key=canonical_value(value),
                record_id=record.id,
            ))
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            if "uq_eos_v2_record_unique_value" in str(exc.orig):
                raise UniqueValueConflict("Unique field value already exists") from exc
            raise

    def get(self, record_id: UUID) -> DynamicRecord:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(DynamicRecordModel).where(
            DynamicRecordModel.id == record_id,
            DynamicRecordModel.tenant_id == tenant_id,
        ))
        if model is None:
            raise KeyError("Dynamic record not found")
        return DynamicRecord(
            id=model.id, tenant_id=model.tenant_id, entity_id=model.entity_id,
            entity_version=model.entity_version, data=from_storage(dict(model.data)),
            row_version=model.row_version, created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def relationship_exists(self, record_id: UUID, entity_id: UUID) -> bool:
        tenant_id = get_tenant_context().tenant_id
        return self.session.scalar(select(DynamicRecordModel.id).where(
            DynamicRecordModel.id == record_id,
            DynamicRecordModel.tenant_id == tenant_id,
            DynamicRecordModel.entity_id == entity_id,
        )) is not None

    def update(
        self,
        record: DynamicRecord,
        expected_row_version: int,
        unique_values: dict[str, Any] | None = None,
    ) -> bool:
        tenant_id = get_tenant_context().tenant_id
        result = self.session.execute(update(DynamicRecordModel).where(
            DynamicRecordModel.id == record.id,
            DynamicRecordModel.tenant_id == tenant_id,
            DynamicRecordModel.row_version == expected_row_version,
        ).values(
            data=to_storage(record.data), row_version=record.row_version,
            updated_at=datetime.now(timezone.utc),
        ))
        if result.rowcount != 1:
            return False

        self.session.execute(delete(DynamicRecordUniqueValueModel).where(
            DynamicRecordUniqueValueModel.tenant_id == tenant_id,
            DynamicRecordUniqueValueModel.entity_id == record.entity_id,
            DynamicRecordUniqueValueModel.record_id == record.id,
        ))
        for field_name, value in (unique_values or {}).items():
            if value is None:
                continue
            self.session.add(DynamicRecordUniqueValueModel(
                tenant_id=tenant_id, entity_id=record.entity_id,
                field_name=field_name, value_key=canonical_value(value),
                record_id=record.id,
            ))
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            if "uq_eos_v2_record_unique_value" in str(exc.orig):
                raise UniqueValueConflict("Unique field value already exists") from exc
            raise
        return True

    def delete(self, record_id: UUID, expected_row_version: int) -> bool:
        tenant_id = get_tenant_context().tenant_id
        result = self.session.execute(delete(DynamicRecordModel).where(
            DynamicRecordModel.id == record_id,
            DynamicRecordModel.tenant_id == tenant_id,
            DynamicRecordModel.row_version == expected_row_version,
        ))
        if result.rowcount != 1:
            return False
        self.session.execute(delete(DynamicRecordUniqueValueModel).where(
            DynamicRecordUniqueValueModel.tenant_id == tenant_id,
            DynamicRecordUniqueValueModel.record_id == record_id,
        ))
        return True
