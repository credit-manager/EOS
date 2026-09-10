from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MetadataField(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    type: str = Field(pattern=r"^(text|integer|decimal|boolean|date|uuid)$")
    required: bool = False
    label: str | None = None


class MetadataDefinition(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    fields: list[MetadataField] = Field(min_length=1, max_length=100)


class MetadataResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    version: int
    definition: dict[str, Any]
    published: bool

    model_config = {"from_attributes": True}
