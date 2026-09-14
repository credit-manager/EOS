from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_EVENT_TYPE_PATTERN = r"^[a-z0-9]+(\.[a-z0-9_]+)+$"
_CONDITION_OPS = Literal[
    "exists", "eq", "neq", "gt", "gte", "lt", "lte", "contains", "not_contains", "in", "starts_with"
]


class Condition(BaseModel):
    field: str = Field(min_length=1, description="Path like 'payload.amount' or 'event.entity_type'")
    op: _CONDITION_OPS
    value: Any = None


class NotifyAction(BaseModel):
    type: Literal["notify"] = "notify"
    title: str = Field(default="Alert", max_length=500)
    message: str = Field(default="", max_length=2000)
    user_id: UUID | None = None
    role: str | None = Field(default=None, max_length=50)


class PublishEventAction(BaseModel):
    type: Literal["publish_event"] = "publish_event"
    event_type: str = Field(min_length=1, max_length=120, pattern=_EVENT_TYPE_PATTERN)
    payload: dict[str, Any] | None = None
    entity_type: str | None = Field(default=None, max_length=120)
    entity_id: str | None = Field(default=None, max_length=64)


class AuditAction(BaseModel):
    type: Literal["audit"] = "audit"
    message: str | None = Field(default=None, max_length=500)


RuleAction = Annotated[
    Annotated[NotifyAction, Field(discriminator="type")]
    | Annotated[PublishEventAction, Field(discriminator="type")]
    | Annotated[AuditAction, Field(discriminator="type")],
    "RuleAction",
]


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_type: str = Field(min_length=1, max_length=120, pattern=_EVENT_TYPE_PATTERN)
    conditions: list[Condition] = Field(default_factory=list)
    actions: list[RuleAction]
    priority: int = Field(default=100, ge=0, le=10000)
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    event_type: str | None = Field(default=None, min_length=1, max_length=120, pattern=_EVENT_TYPE_PATTERN)
    conditions: list[Condition] | None = None
    actions: list[RuleAction] | None = None
    priority: int | None = Field(default=None, ge=0, le=10000)
    enabled: bool | None = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    event_type: str
    conditions: list[Condition] = Field(default_factory=list)
    actions: list[RuleAction]
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    items: list[RuleResponse]
    total: int
    limit: int
    offset: int


class RuleExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    rule_name: str
    triggered_event_id: UUID | None = None
    matched: bool
    detail: str | None = None
    executed_at: datetime


class ExecutionListResponse(BaseModel):
    items: list[RuleExecutionResponse]
    total: int
    limit: int
    offset: int