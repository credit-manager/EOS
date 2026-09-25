from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Policy Engine V2 - WHEN/IF/THEN/ELSE types
TriggerType = Literal[
    "record.created", "record.updated", "record.deleted",
    "workflow.started", "workflow.completed", "workflow.failed",
    "event.published", "schedule.cron", "manual",
]

ConditionOperator = Literal[
    "eq", "neq", "gt", "gte", "lt", "lte",
    "in", "not_in", "contains", "not_contains",
    "starts_with", "ends_with", "regex", "is_null", "is_not_null",
    "and", "or", "not",
]

ActionType = Literal[
    "update_record", "create_record", "send_email", "call_webhook",
    "run_workflow", "delay", "condition", "notify", "publish_event",
    "audit", "transform",
]


class WhenClause(BaseModel):
    """WHEN clause - defines when a policy should be evaluated"""
    trigger: TriggerType
    entity_type: str | None = Field(default=None, max_length=100)
    entity_ids: list[str] | None = None


class Condition(BaseModel):
    """Single condition in IF clause"""
    field: str = Field(min_length=1, max_length=200)
    operator: ConditionOperator
    value: Any = None
    negate: bool = False


class IfClause(BaseModel):
    """IF clause - defines conditions for policy execution"""
    logic: Literal["and", "or"] = "and"
    conditions: list[Condition] = Field(min_length=1, max_length=50)


class Action(BaseModel):
    """Action to execute in THEN/ELSE clause"""
    type: ActionType
    params: dict[str, Any] = Field(default_factory=dict)
    async_execution: bool = False
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_delay_ms: int = Field(default=1000, ge=0, le=60000)


class ThenClause(BaseModel):
    """THEN clause - actions to execute when conditions are met"""
    actions: list[Action] = Field(min_length=1, max_length=20)
    stop_on_failure: bool = True


class ElseClause(BaseModel):
    """ELSE clause - actions to execute when conditions are not met"""
    actions: list[Action] = Field(default_factory=list, max_length=20)


class PolicyDefinition(BaseModel):
    """Full policy definition"""
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=1000)

    when: WhenClause
    if_: IfClause = Field(alias="if")
    then: ThenClause
    else_: ElseClause | None = Field(default=None, alias="else")

    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)

    model_config = {"populate_by_name": True}


class PolicyResponse(BaseModel):
    """Response model for policies"""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None = None
    enabled: bool
    priority: int
    when: WhenClause
    if_: IfClause = Field(alias="if")
    then: ThenClause
    else_: ElseClause | None = Field(default=None, alias="else")
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True, "populate_by_name": True}


class PolicySummary(BaseModel):
    """Summary model for policies"""
    id: UUID
    code: str
    name: str
    enabled: bool
    priority: int
    trigger: TriggerType
    category: str | None = None
    created_at: Any

    model_config = {"from_attributes": True}


class PolicyExecutionResponse(BaseModel):
    """Response model for policy executions"""
    id: UUID
    policy_id: UUID
    policy_code: str
    trigger_event: str
    trigger_resource_type: str | None = None
    trigger_resource_id: str | None = None
    matched: bool
    actions_executed: dict
    execution_time_ms: int | None = None
    error_message: str | None = None
    created_at: Any

    model_config = {"from_attributes": True}
