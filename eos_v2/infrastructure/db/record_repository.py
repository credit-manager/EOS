from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.records import DynamicRecord
from eos_v2.infrastructure.db.record_models import DynamicRecordModel


class SqlAlchemyRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, record: DynamicRecord) -> None:
        tenant_id = get_tenant_context().tenant_id
        if record.tenant_id != tenant_id:
            raise PermissionError("Record tenant does not match current tenant")
        self.session.add(DynamicRecordModel(
            id=record.id, tenant_id=tenant_id, entity_id=record.entity_id,
            entity_version=record.entity_version, data=record.data,
            row_version=record.row_version, created_at=record.created_at,
            updated_at=record.updated_at,
        ))

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
            entity_version=model.entity_version, data=dict(model.data),
            row_version=model.row_version, created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def update(self, record: DynamicRecord, expected_row_version: int) -> bool:
        tenant_id = get_tenant_context().tenant_id
        result = self.session.execute(update(DynamicRecordModel).where(
            DynamicRecordModel.id == record.id,
            DynamicRecordModel.tenant_id == tenant_id,
            DynamicRecordModel.row_version == expected_row_version,
        ).values(
            data=record.data, row_version=record.row_version,
            updated_at=datetime.now(timezone.utc),
        ))
        return result.rowcount == 1

    def delete(self, record_id: UUID, expected_row_version: int) -> bool:
        tenant_id = get_tenant_context().tenant_id
        result = self.session.execute(delete(DynamicRecordModel).where(
            DynamicRecordModel.id == record_id,
            DynamicRecordModel.tenant_id == tenant_id,
            DynamicRecordModel.row_version == expected_row_version,
        ))
        return result.rowcount == 1
