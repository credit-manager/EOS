from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from .reserved_names import SYSTEM_OWNED_NAMES


class FieldType(str, Enum):
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    name: str
    field_type: FieldType
    required: bool = False
    unique: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum() or self.name[0].isdigit():
            raise ValueError("Field name must be a valid identifier")
        if self.name in SYSTEM_OWNED_NAMES:
            raise ValueError(f"Field name is system-owned: {self.name}")


@dataclass(frozen=True, slots=True)
class RelationshipDefinition:
    name: str
    target_entity_id: UUID
    required: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum() or self.name[0].isdigit():
            raise ValueError("Relationship name must be a valid identifier")
        if self.name in SYSTEM_OWNED_NAMES:
            raise ValueError(f"Relationship name is system-owned: {self.name}")


@dataclass(frozen=True, slots=True)
class EntityDefinition:
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    name: str = ""
    label: str = ""
    version: int = 1
    fields: tuple[FieldDefinition, ...] = ()
    relationships: tuple[RelationshipDefinition, ...] = ()
    published: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum() or self.name[0].isdigit():
            raise ValueError("Entity name must be a valid identifier")
        if self.version < 1:
            raise ValueError("Entity version must be positive")
        names = [item.name for item in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique within an entity")
        relationship_names = [item.name for item in self.relationships]
        if len(relationship_names) != len(set(relationship_names)):
            raise ValueError("Relationship names must be unique within an entity")
        overlap = set(names) & set(relationship_names)
        if overlap:
            raise ValueError(f"Field and relationship names must be unique: {', '.join(sorted(overlap))}")
