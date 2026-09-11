from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "integer", "decimal", "boolean", "date", "uuid", "relation"]
PermissionAction = Literal["create", "read", "update", "delete"]


class MetadataField(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    type: FieldType
    required: bool = False
    nullable: bool = False
    label: str | None = Field(default=None, max_length=200)
    target_entity: str | None = Field(default=None, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")

    @model_validator(mode="after")
    def validate_relation_target(self) -> "MetadataField":
        if self.type == "relation" and not self.target_entity:
            raise ValueError("relation fields require target_entity")
        if self.type != "relation" and self.target_entity is not None:
            raise ValueError("target_entity is only valid for relation fields")
        return self


class MetadataPermissions(BaseModel):
    admin: list[PermissionAction] = Field(default_factory=lambda: ["create", "read", "update", "delete"])
    member: list[PermissionAction] = Field(default_factory=lambda: ["create", "read", "update", "delete"])

    @model_validator(mode="after")
    def validate_actions(self) -> "MetadataPermissions":
        for role, actions in (("admin", self.admin), ("member", self.member)):
            if len(actions) != len(set(actions)):
                raise ValueError(f"duplicate permission actions for {role}")
            if "read" not in actions:
                raise ValueError(f"read permission is required for {role}")
        return self


class MetadataDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[MetadataField] = Field(min_length=1, max_length=100)
    permissions: MetadataPermissions = Field(default_factory=MetadataPermissions)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "MetadataDefinition":
        codes = [field.code for field in self.fields]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ValueError(f"duplicate field codes: {', '.join(duplicates)}")
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
