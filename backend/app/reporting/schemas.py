from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ..rules.schemas import Condition

Metric = Literal["count", "sum", "avg", "min", "max"]


class AnalyticsReportCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=200)
    entity_code: str = Field(min_length=1, max_length=100)
    metric: Metric
    field: str | None = Field(default=None, max_length=100)
    conditions: list[Condition] = Field(default_factory=list, max_length=20)
    group_by: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def value_metric_requires_field(self):
        if self.metric != "count" and not self.field:
            raise ValueError("field is required when metric is not count")
        return self


class AnalyticsReportUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    metric: Metric | None = None
    field: str | None = Field(default=None, max_length=100)
    conditions: list[Condition] | None = Field(default=None, max_length=20)
    group_by: str | None = Field(default=None, max_length=100)


class AnalyticsReportResponse(BaseModel):
    id: UUID
    code: str
    name: str
    entity_code: str
    metric: Metric
    field: str | None
    conditions: list[Condition]
    group_by: str | None
    created_by: UUID | None
    created_at: datetime


class SeriesItem(BaseModel):
    key: str
    value: Decimal | None


class ReportRunResult(BaseModel):
    report_code: str
    report_name: str
    entity_code: str
    metric: Metric
    field: str | None
    value: Decimal | None
    count: int
    series: list[SeriesItem]
    refs: list[str]


class ReportRunResponse(BaseModel):
    run_id: UUID
    report_code: str
    result: ReportRunResult
    created_at: datetime


class EntityCounter(BaseModel):
    entity_code: str
    count: int


class WorkflowAttention(BaseModel):
    instance_id: UUID
    workflow_code: str
    current_state: str
    status: str


class PendingApproval(BaseModel):
    task_id: UUID
    instance_id: UUID
    workflow_code: str
    action: str
    from_state: str
    to_state: str
    requested_at: datetime
    roles: list[str]


class WorkspaceFeed(BaseModel):
    entity_counts: list[EntityCounter]
    approvals_pending: list[PendingApproval]
    workflows_needing_action: list[WorkflowAttention]
    recent_events: list[dict]
    recent_rule_firings: list[dict]
    report_count: int