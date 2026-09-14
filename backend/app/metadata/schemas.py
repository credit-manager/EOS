from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "integer", "decimal", "boolean", "date", "uuid", "relation"]
PermissionAction = Literal["create", "read", "update", "delete"]
_COMPUTABLE_TYPES = {"integer", "decimal"}


class FieldComputed(BaseModel):
    formula: str = Field(min_length=1, max_length=500)


class FieldValidation(BaseModel):
    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = Field(default=None, max_length=500)
    min_length: int | None = None
    max_length: int | None = None


class MetadataField(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    type: FieldType
    required: bool = False
    nullable: bool = False
    label: str | None = Field(default=None, max_length=200)
    target_entity: str | None = Field(default=None, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    computed: FieldComputed | None = None
    validation: FieldValidation | None = None
    default: Any = None
    readonly: bool = False

    @model_validator(mode="after")
    def validate_relation_target(self) -> "MetadataField":
        if self.type == "relation" and not self.target_entity:
            raise ValueError("relation fields require target_entity")
        if self.type != "relation" and self.target_entity is not None:
            raise ValueError("target_entity is only valid for relation fields")
        return self

    @model_validator(mode="after")
    def validate_computed_type(self) -> "MetadataField":
        if self.computed is not None and self.type not in _COMPUTABLE_TYPES:
            raise ValueError(f"computed fields require numeric type ({', '.join(sorted(_COMPUTABLE_TYPES))})")
        if self.computed is not None and self.readonly is False:
            self.readonly = True
        if self.readonly and self.computed is None:
            raise ValueError("readonly without computed is not allowed yet")
        return self

    @model_validator(mode="after")
    def validate_relation_not_computed(self) -> "MetadataField":
        if self.computed is not None and self.type == "relation":
            raise ValueError("relation fields cannot be computed")
        return self


class MetadataPermissions(BaseModel):
    admin: list[PermissionAction] = Field(default_factory=lambda: ["create", "read", "update", "delete"])
    member: list[PermissionAction] = Field(default_factory=lambda: ["create", "read", "update", "delete"])

    @model_validator(mode="after")
    def validate_actions(self) -> "MetadataPermissions":
        if len(self.admin) != len(set(self.admin)):
            raise ValueError("duplicate permission actions for admin")
        if "read" not in self.admin:
            raise ValueError("read permission is required for admin")
        if len(self.member) != len(set(self.member)):
            raise ValueError("duplicate permission actions for member")
        return self


class MetadataWorkflowBinding(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    reference_type: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    auto_start_on_create: bool = True


class FieldGroup(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[str] = Field(min_length=1, max_length=50)


class MetadataDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[MetadataField] = Field(min_length=1, max_length=100)
    permissions: MetadataPermissions = Field(default_factory=MetadataPermissions)
    workflow: MetadataWorkflowBinding | None = None
    groups: list[FieldGroup] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "MetadataDefinition":
        codes = [field.code for field in self.fields]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ValueError(f"duplicate field codes: {', '.join(duplicates)}")
        return self

    @model_validator(mode="after")
    def validate_groups_reference_valid_fields(self) -> "MetadataDefinition":
        field_codes = {field.code for field in self.fields}
        for group in self.groups:
            unknown = set(group.fields) - field_codes
            if unknown:
                raise ValueError(f"group {group.code!r} references unknown fields: {sorted(unknown)}")
        return self

    @model_validator(mode="after")
    def validate_groups_unique_fields(self) -> "MetadataDefinition":
        seen: set[str] = set()
        for group in self.groups:
            overlap = seen & set(group.fields)
            if overlap:
                raise ValueError(f"group {group.code!r} shares fields with earlier groups: {sorted(overlap)}")
            seen |= set(group.fields)
        return self


class MetadataResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    version: int
    definition: dict[str, Any]
    published: bool

    model_config = {"from_attributes": True}


class MetadataSummary(BaseModel):
    id: UUID
    code: str
    name: str
    version: int
    field_count: int
    permissions: MetadataPermissions

    model_config = {"from_attributes": True}
