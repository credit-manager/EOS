from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    ref: str
    entity_code: str
    record_id: UUID
    title: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    field: str
    target_entity: str


class GraphStory(BaseModel):
    root: GraphNode
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    depth: int
