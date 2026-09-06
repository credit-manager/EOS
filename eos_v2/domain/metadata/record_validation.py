from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from eos_v2.domain.metadata.entities import EntityDefinition, FieldType


class RecordValidationError(ValueError):
    """Raised when dynamic record data does not satisfy its metadata contract."""


def _matches(value: Any, field_type: FieldType) -> bool:
    if field_type is FieldType.TEXT:
        return isinstance(value, str)
    if field_type is FieldType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type is FieldType.DECIMAL:
        return isinstance(value, (Decimal, int, float)) and not isinstance(value, bool)
    if field_type is FieldType.BOOLEAN:
        return isinstance(value, bool)
    if field_type is FieldType.DATE:
        return isinstance(value, date) and not isinstance(value, datetime)
    if field_type is FieldType.DATETIME:
        return isinstance(value, datetime)
    if field_type is FieldType.UUID:
        return isinstance(value, UUID)
    if field_type is FieldType.JSON:
        return isinstance(value, (dict, list, str, int, float, bool)) or value is None
    return False


def validate_record(definition: EntityDefinition, data: dict[str, Any]) -> None:
    field_map = {field.name: field for field in definition.fields}
    relationship_map = {relationship.name: relationship for relationship in definition.relationships}
    allowed = set(field_map) | set(relationship_map)
    unknown = set(data) - allowed
    if unknown:
        raise RecordValidationError(f"Unknown fields: {', '.join(sorted(unknown))}")

    for field in definition.fields:
        value = data.get(field.name)
        if value is None:
            if field.required:
                raise RecordValidationError(f"Required field missing: {field.name}")
            continue
        if not _matches(value, field.field_type):
            raise RecordValidationError(f"Invalid type for field: {field.name}")

    for relationship in definition.relationships:
        if relationship.required and relationship.name not in data:
            raise RecordValidationError(f"Required relationship missing: {relationship.name}")
        if relationship.name in data:
            value = data[relationship.name]
            if not isinstance(value, UUID):
                raise RecordValidationError(f"Invalid relationship value: {relationship.name}")
