"""EOS Builder schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class BuilderObjectCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    object_type: str = Field(default="entity", max_length=50)
    parent_object_id: str | None = None
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=20)
    config: dict | None = None


class BuilderObjectResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None = None
    object_type: str
    parent_object_id: str | None = None
    icon: str | None = None
    color: str | None = None
    is_system: bool
    is_active: bool
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderFieldCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    field_type: str = Field(..., max_length=50)
    is_required: bool = False
    is_unique: bool = False
    default_value: str | None = None
    options: dict | None = None
    validation_rules: dict | None = None
    display_config: dict | None = None
    sort_order: int = 0


class BuilderFieldResponse(BaseModel):
    id: str
    object_id: str
    code: str
    name: str
    description: str | None = None
    field_type: str
    is_required: bool
    is_unique: bool
    default_value: str | None = None
    options: dict | None = None
    validation_rules: dict | None = None
    display_config: dict | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderRelationCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    source_object_id: str = Field(..., min_length=1)
    target_object_id: str = Field(..., min_length=1)
    relation_type: str = Field(..., max_length=50)
    source_field: str | None = Field(default=None, max_length=100)
    target_field: str | None = Field(default=None, max_length=100)
    is_required: bool = False
    cascade_delete: bool = False
    display_config: dict | None = None


class BuilderRelationResponse(BaseModel):
    id: str
    code: str
    name: str
    source_object_id: str
    target_object_id: str
    relation_type: str
    source_field: str | None = None
    target_field: str | None = None
    is_required: bool
    cascade_delete: bool
    display_config: dict | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BuilderWorkflowCreate(BaseModel):
    object_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str = Field(..., max_length=50)
    trigger_config: dict | None = None
    steps: list[dict] | None = None


class BuilderWorkflowResponse(BaseModel):
    id: str
    tenant_id: str
    object_id: str
    code: str
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict | None = None
    steps: list[dict] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderRuleCreate(BaseModel):
    object_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    rule_type: str = Field(..., max_length=50)
    when_clause: dict | None = None
    if_clause: dict | None = None
    then_actions: list[dict] | None = None
    else_actions: list[dict] | None = None
    priority: int = 0


class BuilderRuleResponse(BaseModel):
    id: str
    tenant_id: str
    object_id: str
    code: str
    name: str
    description: str | None = None
    rule_type: str
    when_clause: dict | None = None
    if_clause: dict | None = None
    then_actions: list[dict] | None = None
    else_actions: list[dict] | None = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderViewCreate(BaseModel):
    object_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    view_type: str = Field(..., max_length=50)
    columns: list[dict] | None = None
    filters: list[dict] | None = None
    sorts: list[dict] | None = None
    layout: dict | None = None
    is_default: bool = False


class BuilderViewResponse(BaseModel):
    id: str
    tenant_id: str
    object_id: str
    code: str
    name: str
    description: str | None = None
    view_type: str
    columns: list[dict] | None = None
    filters: list[dict] | None = None
    sorts: list[dict] | None = None
    layout: dict | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderDashboardCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    layout: dict | None = None
    widgets: list[dict] | None = None
    is_default: bool = False


class BuilderDashboardResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None = None
    layout: dict | None = None
    widgets: list[dict] | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderWidgetCreate(BaseModel):
    dashboard_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    widget_type: str = Field(..., max_length=50)
    config: dict | None = None
    data_source: dict | None = None
    position: dict | None = None


class BuilderWidgetResponse(BaseModel):
    id: str
    dashboard_id: str
    code: str
    name: str
    widget_type: str
    config: dict | None = None
    data_source: dict | None = None
    position: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderAutomationCreate(BaseModel):
    object_id: str | None = None
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    trigger_type: str = Field(..., max_length=50)
    trigger_config: dict | None = None
    conditions: list[dict] | None = None
    actions: list[dict] | None = None


class BuilderAutomationResponse(BaseModel):
    id: str
    tenant_id: str
    object_id: str | None = None
    code: str
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict | None = None
    conditions: list[dict] | None = None
    actions: list[dict] | None = None
    is_active: bool
    last_run_at: datetime | None = None
    run_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuilderExportRequest(BaseModel):
    export_type: str = Field(..., max_length=50)
    export_format: str = Field(default="json", max_length=20)
    config: dict | None = None


class BuilderExportResponse(BaseModel):
    id: str
    tenant_id: str
    export_type: str
    export_format: str
    config: dict | None = None
    status: str
    file_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class BuilderSchemaExport(BaseModel):
    objects: list[BuilderObjectResponse]
    fields: list[BuilderFieldResponse]
    relations: list[BuilderRelationResponse]
    workflows: list[BuilderWorkflowResponse]
    rules: list[BuilderRuleResponse]
    views: list[BuilderViewResponse]
    dashboards: list[BuilderDashboardResponse]
    automations: list[BuilderAutomationResponse]
