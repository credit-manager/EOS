from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from eos_v2.domain.metadata.entities import EntityDefinition, FieldType
from eos_v2.domain.metadata.record_validation import RecordValidationError


def coerce_record_data(definition: EntityDefinition, data: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON transport primitives into domain-native metadata values."""
    result = dict(data)
    field_map = {field.name: field for field in definition.fields}
    for name, field in field_map.items():
        if name not in result or result[name] is None:
            continue
        value = result[name]
        try:
            if field.field_type is FieldType.UUID and isinstance(value, str):
                result[name] = UUID(value)
            elif field.field_type is FieldType.DATE and isinstance(value, str):
                result[name] = date.fromisoformat(value)
            elif field.field_type is FieldType.DATETIME and isinstance(value, str):
                result[name] = datetime.fromisoformat(value)
            elif field.field_type is FieldType.DECIMAL and isinstance(value, str):
                result[name] = Decimal(value)
        except (TypeError, ValueError) as exc:
            raise RecordValidationError(f"Invalid value for field: {name}") from exc

    for relationship in definition.relationships:
        if relationship.name in result and isinstance(result[relationship.name], str):
            try:
                result[relationship.name] = UUID(result[relationship.name])
            except (TypeError, ValueError) as exc:
                raise RecordValidationError(f"Invalid relationship value: {relationship.name}") from exc
    return result
