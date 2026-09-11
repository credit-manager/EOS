from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class RecordUpdate(BaseModel):
    data: dict[str, Any]
    version: int = Field(ge=1)


class RecordResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    entity_code: str
    data: dict[str, Any]
    version: int
    workflow_instance_id: UUID | None = None

    model_config = {"from_attributes": True}
