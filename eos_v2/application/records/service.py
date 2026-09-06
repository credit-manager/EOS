from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition
from eos_v2.domain.metadata.record_validation import validate_record
from eos_v2.domain.metadata.records import DynamicRecord


class RecordRepository(Protocol):
    def add(self, record: DynamicRecord, unique_values: dict[str, Any] | None = None) -> None: ...
    def get(self, record_id: UUID) -> DynamicRecord: ...
    def relationship_exists(self, record_id: UUID, entity_id: UUID) -> bool: ...
    def update(self, record: DynamicRecord, expected_row_version: int, unique_values: dict[str, Any] | None = None) -> bool: ...
    def delete(self, record_id: UUID, expected_row_version: int) -> bool: ...


class InMemoryRecordRepository:
    """Small deterministic repository used by domain/application tests."""

    def __init__(self) -> None:
        self.records: dict[UUID, DynamicRecord] = {}

    def add(self, record: DynamicRecord, unique_values: dict[str, Any] | None = None) -> None:
        if record.id in self.records:
            raise ValueError("Record already exists")
        for existing in self.records.values():
            if existing.tenant_id != record.tenant_id or existing.entity_id != record.entity_id:
                continue
            for field_name, value in (unique_values or {}).items():
                if value is not None and existing.data.get(field_name) == value:
                    raise ValueError("Unique field value already exists")
        self.records[record.id] = record

    def get(self, record_id: UUID) -> DynamicRecord:
        record = self.records.get(record_id)
        if record is None:
            raise KeyError("Dynamic record not found")
        return record

    def relationship_exists(self, record_id: UUID, entity_id: UUID) -> bool:
        record = self.records.get(record_id)
        context = get_tenant_context()
        return record is not None and record.tenant_id == context.tenant_id and record.entity_id == entity_id

    def update(self, record: DynamicRecord, expected_row_version: int, unique_values: dict[str, Any] | None = None) -> bool:
        current = self.records.get(record.id)
        if current is None or current.row_version != expected_row_version:
            return False
        for existing in self.records.values():
            if existing.id == record.id or existing.tenant_id != record.tenant_id or existing.entity_id != record.entity_id:
                continue
            for field_name, value in (unique_values or {}).items():
                if value is not None and existing.data.get(field_name) == value:
                    raise ValueError("Unique field value already exists")
        self.records[record.id] = record
        return True

    def delete(self, record_id: UUID, expected_row_version: int) -> bool:
        current = self.records.get(record_id)
        if current is None or current.row_version != expected_row_version:
            return False
        del self.records[record_id]
        return True


class DynamicRecordService:
    def __init__(self, repository: RecordRepository) -> None:
        self.repository = repository

    @staticmethod
    def _unique_values(definition: EntityDefinition, data: dict[str, Any]) -> dict[str, Any]:
        return {field.name: data.get(field.name) for field in definition.fields if field.unique and field.name in data}

    def _validate_relationships(self, definition: EntityDefinition, data: dict[str, Any]) -> None:
        for relationship in definition.relationships:
            if relationship.name not in data:
                continue
            target_id = data[relationship.name]
            if not self.repository.relationship_exists(target_id, relationship.target_entity_id):
                raise ValueError(f"Relationship target not found: {relationship.name}")

    def create(self, definition: EntityDefinition, data: dict[str, Any]) -> DynamicRecord:
        tenant_id = get_tenant_context().tenant_id
        if definition.tenant_id != tenant_id:
            raise PermissionError("Metadata tenant does not match current tenant")
        if not definition.published:
            raise ValueError("Only published metadata can accept records")
        validate_record(definition, data)
        self._validate_relationships(definition, data)
        record = DynamicRecord(
            tenant_id=tenant_id,
            entity_id=definition.id,
            entity_version=definition.version,
            data=dict(data),
        )
        self.repository.add(record, self._unique_values(definition, data))
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
        self._validate_relationships(definition, data)
        updated = DynamicRecord(
            id=record.id,
            tenant_id=record.tenant_id,
            entity_id=record.entity_id,
            entity_version=record.entity_version,
            data=dict(data),
            row_version=record.row_version + 1,
            created_at=record.created_at,
        )
        if not self.repository.update(updated, expected_row_version, self._unique_values(definition, data)):
            raise RuntimeError("Stale record version")
        return updated

    def delete(self, record_id: UUID, expected_row_version: int) -> None:
        self.get(record_id)
        if not self.repository.delete(record_id, expected_row_version):
            raise RuntimeError("Stale record version")
