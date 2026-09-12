from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

FieldType = Literal[
    "text", "integer", "decimal", "boolean", "date", "uuid", "relation",
    "enum", "email", "url", "json", "array",
]
PermissionAction = Literal["create", "read", "update", "delete"]
WidgetType = Literal[
    "text", "textarea", "select", "multiselect", "datepicker",
    "file_upload", "email", "url", "json_editor", "checkbox",
]


class MetadataField(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    type: FieldType
    required: bool = False
    nullable: bool = False
    label: str | None = Field(default=None, max_length=200)
    target_entity: str | None = Field(default=None, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")

    # Rendering hints
    widget: WidgetType | None = None
    placeholder: str | None = Field(default=None, max_length=200)
    help_text: str | None = Field(default=None, max_length=500)

    # Enum/multi-select options: list of {value, label} pairs
    options: list[dict[str, str]] | None = None

    # Validation constraints
    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = Field(default=None, max_length=200)

    # Default value
    default: Any = None

    # Field grouping for UI sections
    group: str | None = Field(default=None, max_length=100)

    # Array item type (for array fields)
    item_type: FieldType | None = None

    @model_validator(mode="after")
    def validate_relation_target(self) -> "MetadataField":
        if self.type == "relation" and not self.target_entity:
            raise ValueError("relation fields require target_entity")
        if self.type != "relation" and self.target_entity is not None:
            raise ValueError("target_entity is only valid for relation fields")
        return self

    @model_validator(mode="after")
    def validate_enum_options(self) -> "MetadataField":
        if self.type == "enum" and not self.options:
            raise ValueError("enum fields require options list")
        if self.type == "enum" and self.options:
            values = [opt.get("value") for opt in self.options]
            if len(values) != len(set(values)):
                raise ValueError("enum options must have unique values")
        if self.type != "enum" and self.options is not None:
            raise ValueError("options is only valid for enum fields")
        return self

    @model_validator(mode="after")
    def validate_array_item_type(self) -> "MetadataField":
        if self.type == "array" and not self.item_type:
            raise ValueError("array fields require item_type")
        if self.type != "array" and self.item_type is not None:
            raise ValueError("item_type is only valid for array fields")
        return self

    @model_validator(mode="after")
    def validate_widget_compat(self) -> "MetadataField":
        if self.widget is None:
            return self
        widget_map = {
            "text": {"text"},
            "textarea": {"text"},
            "select": {"enum"},
            "multiselect": {"enum"},
            "datepicker": {"date"},
            "file_upload": {"text"},
            "email": {"email", "text"},
            "url": {"url", "text"},
            "json_editor": {"json"},
            "checkbox": {"boolean"},
        }
        allowed = widget_map.get(self.widget, set())
        if self.type not in allowed:
            raise ValueError(f"widget '{self.widget}' is not compatible with type '{self.type}'")
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


class MetadataDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[MetadataField] = Field(min_length=1, max_length=100)
    permissions: MetadataPermissions = Field(default_factory=MetadataPermissions)
    workflow: MetadataWorkflowBinding | None = None
    groups: list[str] | None = None

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
