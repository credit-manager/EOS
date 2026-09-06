"""Metadata kernel domain primitives."""

from .entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from .record_validation import RecordValidationError, validate_record
from .records import DynamicRecord

__all__ = [
    "EntityDefinition", "FieldDefinition", "FieldType", "RelationshipDefinition",
    "DynamicRecord", "RecordValidationError", "validate_record",
]
