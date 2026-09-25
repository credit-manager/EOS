from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Metadata Engine V2 - Extended field types
FieldType = Literal[
    # Basic types
    "text", "integer", "decimal", "boolean", "date", "uuid", "relation",
    # Extended types (V2)
    "computed", "select", "multi_select", "json", "file",
    "email", "phone", "url", "rich_text", "currency",
    "percentage", "duration", "location", "rating",
]
PermissionAction = Literal["create", "read", "update", "delete"]
_COMPUTABLE_TYPES = {"integer", "decimal", "currency", "percentage"}
_SELECTABLE_TYPES = {"select", "multi_select"}
_FILE_TYPES = {"file"}
_CONTACT_TYPES = {"email", "phone"}
_SPECIAL_TYPES = {"location", "rating", "duration"}


class FieldComputed(BaseModel):
    formula: str = Field(min_length=1, max_length=500)


class FieldValidation(BaseModel):
    min: int | float | None = None
    max: int | float | None = None
    pattern: str | None = Field(default=None, max_length=500)
    min_length: int | None = None
    max_length: int | None = None


class FieldPermissions(BaseModel):
    """Field-level permissions for Metadata Engine V2"""
    read: list[str] = Field(default_factory=lambda: ["admin", "member"])
    write: list[str] = Field(default_factory=lambda: ["admin"])
    hidden: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_permissions(self) -> "FieldPermissions":
        if len(self.read) != len(set(self.read)):
            raise ValueError("duplicate read permissions")
        if len(self.write) != len(set(self.write)):
            raise ValueError("duplicate write permissions")
        if len(self.hidden) != len(set(self.hidden)):
            raise ValueError("duplicate hidden permissions")
        return self


class SelectOption(BaseModel):
    """Option for select/multi_select fields"""
    value: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    color: str | None = Field(default=None, max_length=20)
    icon: str | None = Field(default=None, max_length=50)


class FileConfig(BaseModel):
    """Configuration for file fields"""
    allowed_types: list[str] = Field(default_factory=lambda: ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "png"])
    max_size_mb: int = Field(default=10, ge=1, le=100)
    multiple: bool = False


class LocationConfig(BaseModel):
    """Configuration for location fields"""
    lat: float | None = None
    lng: float | None = None
    address: str | None = None


class RatingConfig(BaseModel):
    """Configuration for rating fields"""
    min_value: int = Field(default=1, ge=0)
    max_value: int = Field(default=5, le=10)
    step: float = Field(default=1, ge=0.1)


class DurationConfig(BaseModel):
    """Configuration for duration fields"""
    unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months"] = "hours"


class CurrencyConfig(BaseModel):
    """Configuration for currency fields"""
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    decimal_places: int = Field(default=2, ge=0, le=4)


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

    # Metadata Engine V2 additions
    permissions: FieldPermissions | None = None
    placeholder: str | None = Field(default=None, max_length=200)
    help_text: str | None = Field(default=None, max_length=500)

    # Type-specific configurations
    select_options: list[SelectOption] | None = None
    file_config: FileConfig | None = None
    location_config: LocationConfig | None = None
    rating_config: RatingConfig | None = None
    duration_config: DurationConfig | None = None
    currency_config: CurrencyConfig | None = None

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

    @model_validator(mode="after")
    def validate_select_options(self) -> "MetadataField":
        if self.type in _SELECTABLE_TYPES and not self.select_options:
            raise ValueError(f"{self.type} fields require select_options")
        if self.type not in _SELECTABLE_TYPES and self.select_options is not None:
            raise ValueError("select_options is only valid for select/multi_select fields")
        return self

    @model_validator(mode="after")
    def validate_file_config(self) -> "MetadataField":
        if self.type in _FILE_TYPES and not self.file_config:
            raise ValueError(f"{self.type} fields require file_config")
        if self.type not in _FILE_TYPES and self.file_config is not None:
            raise ValueError("file_config is only valid for file fields")
        return self

    @model_validator(mode="after")
    def validate_location_config(self) -> "MetadataField":
        if self.type == "location" and not self.location_config:
            raise ValueError("location fields require location_config")
        if self.type != "location" and self.location_config is not None:
            raise ValueError("location_config is only valid for location fields")
        return self

    @model_validator(mode="after")
    def validate_rating_config(self) -> "MetadataField":
        if self.type == "rating" and not self.rating_config:
            raise ValueError("rating fields require rating_config")
        if self.type != "rating" and self.rating_config is not None:
            raise ValueError("rating_config is only valid for rating fields")
        return self

    @model_validator(mode="after")
    def validate_duration_config(self) -> "MetadataField":
        if self.type == "duration" and not self.duration_config:
            raise ValueError("duration fields require duration_config")
        if self.type != "duration" and self.duration_config is not None:
            raise ValueError("duration_config is only valid for duration fields")
        return self

    @model_validator(mode="after")
    def validate_currency_config(self) -> "MetadataField":
        if self.type == "currency" and not self.currency_config:
            raise ValueError("currency fields require currency_config")
        if self.type != "currency" and self.currency_config is not None:
            raise ValueError("currency_config is only valid for currency fields")
        return self

    @model_validator(mode="after")
    def validate_email_format(self) -> "MetadataField":
        if self.type == "email" and self.validation and self.validation.pattern:
            raise ValueError("email fields use built-in validation, pattern not allowed")
        return self

    @model_validator(mode="after")
    def validate_phone_format(self) -> "MetadataField":
        if self.type == "phone" and self.validation and self.validation.pattern:
            raise ValueError("phone fields use built-in validation, pattern not allowed")
        return self

    @model_validator(mode="after")
    def validate_url_format(self) -> "MetadataField":
        if self.type == "url" and self.validation and self.validation.pattern:
            raise ValueError("url fields use built-in validation, pattern not allowed")
        return self

    @model_validator(mode="after")
    def validate_rich_text_readonly(self) -> "MetadataField":
        if self.type == "rich_text" and self.readonly:
            raise ValueError("rich_text fields cannot be readonly")
        return self

    @model_validator(mode="after")
    def validate_json_readonly(self) -> "MetadataField":
        if self.type == "json" and self.readonly:
            raise ValueError("json fields cannot be readonly")
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


class SchemaTemplate(BaseModel):
    """Schema template for Metadata Engine V2"""
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    entity_code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    fields: list[MetadataField] = Field(min_length=1, max_length=100)
    permissions: MetadataPermissions = Field(default_factory=MetadataPermissions)
    groups: list[FieldGroup] = Field(default_factory=list, max_length=20)
    is_builtin: bool = False
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)


class MetadataDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[MetadataField] = Field(min_length=1, max_length=100)
    permissions: MetadataPermissions = Field(default_factory=MetadataPermissions)
    workflow: MetadataWorkflowBinding | None = None
    groups: list[FieldGroup] = Field(default_factory=list, max_length=20)
    template_code: str | None = Field(default=None, max_length=100)

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


class SchemaTemplateResponse(BaseModel):
    """Response model for schema templates"""
    id: UUID
    code: str
    name: str
    description: str | None = None
    entity_code: str
    is_builtin: bool
    category: str | None = None

    model_config = {"from_attributes": True}


class SchemaTemplateSummary(BaseModel):
    """Summary model for schema templates"""
    id: UUID
    code: str
    name: str
    description: str | None = None
    entity_code: str
    is_builtin: bool
    category: str | None = None
    field_count: int

    model_config = {"from_attributes": True}
