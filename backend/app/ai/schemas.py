from typing import Any

from pydantic import BaseModel, Field


class SmartSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=25, ge=1, le=100)


class SmartSearchResult(BaseModel):
    id: str
    data: dict[str, Any]
    score: float
    version: int


class SimilarityResult(BaseModel):
    id: str
    data: dict[str, Any]
    similarity: float
    version: int


class DuplicatePair(BaseModel):
    record_a: str
    record_b: str
    data_a: dict[str, Any]
    data_b: dict[str, Any]
    similarity: float


class AnomalyResult(BaseModel):
    record_id: str
    field: str
    value: float
    mean: float
    std: float
    z_score: float
    direction: str
