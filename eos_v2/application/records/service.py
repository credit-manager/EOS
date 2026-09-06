from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition
from eos_v2.domain.metadata.record_validation import validate_record
from eos_v2.domain.metadata.records import DynamicRecord


class RecordRepository(Protocol):
    def add(self, record: DynamicRecord) -> None: ...
    def get(self, record_id: UUID) -> DynamicRecord: ...
    def update(self, record: DynamicRecord, expected_row_version: int) -> bool: ...
    def delete(self, record_id: UUID, expected_row_version: int) -> bool: ...


class DynamicRecordService:
    def __init__(self, repository: RecordRepository) -> None:
        self.repository = repository

    def create(self, definition: EntityDefinition, data: dict[str, Any]) -> DynamicRecord:
        tenant_id = get_tenant_context().tenant_id
        if definition.tenant_id != tenant_id:
            raise PermissionError("Metadata tenant does not match current tenant")
        if not definition.published:
            raise ValueError("Only published metadata can accept records")
        validate_record(definition, data)
        record = DynamicRecord(
            tenant_id=tenant_id,
            entity_id=definition.id,
            entity_version=definition.version,
            data=dict(data),
        )
        self.repository.add(record)
        return record

    def get(self, record_id: UUID) -> DynamicRecord:
        record = self.repository.get(record_id)
        if record.tenant_id != get_tenant_context().tenant_id:
            raise PermissionError("Cross-tenant access denied")
        return record

    def update(self, definition: EntityDefinition, record_id: UUID, data: dict[str, Any], expected_row_version: int) -> DynamicRecord:
        record = self.get(record_id)
        if record.entity_id != definition.id:
            raise ValueError("Record does not belong to metadata entity")
        validate_record(definition, data)
        updated = DynamicRecord(
            id=record.id,
            tenant_id=record.tenant_id,
            entity_id=record.entity_id,
            entity_version=record.entity_version,
            data=dict(data),
            row_version=record.row_version + 1,
            created_at=record.created_at,
        )
        if not self.repository.update(updated, expected_row_version):
            raise RuntimeError("Stale record version")
        return updated

    def delete(self, record_id: UUID, expected_row_version: int) -> None:
        self.get(record_id)
        if not self.repository.delete(record_id, expected_row_version):
            raise RuntimeError("Stale record version")
