from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/entities/{entity_code}/search", response_model=list[schemas.SmartSearchResult])
def smart_search(
    entity_code: str,
    payload: schemas.SmartSearchRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[schemas.SmartSearchResult]:
    results = service.smart_search(
        db,
        tenant_id=tenant_id,
        entity_code=entity_code,
        query=payload.query,
        limit=payload.limit,
    )
    return [schemas.SmartSearchResult(**r) for r in results]


@router.post("/entities/{entity_code}/records/{record_id}/tags", response_model=list[str])
def auto_tag(
    entity_code: str,
    record_id: UUID,
    max_tags: int = Query(default=10, ge=1, le=50),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[str]:
    return service.auto_tag(
        db,
        tenant_id=tenant_id,
        entity_code=entity_code,
        record_id=record_id,
        max_tags=max_tags,
    )


@router.post("/entities/{entity_code}/records/{record_id}/similar", response_model=list[schemas.SimilarityResult])
def find_similar(
    entity_code: str,
    record_id: UUID,
    limit: int = Query(default=5, ge=1, le=50),
    min_score: float = Query(default=0.1, ge=0.0, le=1.0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[schemas.SimilarityResult]:
    results = service.find_similar(
        db,
        tenant_id=tenant_id,
        entity_code=entity_code,
        record_id=record_id,
        limit=limit,
        min_score=min_score,
    )
    return [schemas.SimilarityResult(**r) for r in results]


@router.post("/entities/{entity_code}/duplicates", response_model=list[schemas.DuplicatePair])
def detect_duplicates(
    entity_code: str,
    threshold: float = Query(default=0.8, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[schemas.DuplicatePair]:
    results = service.detect_duplicates(
        db,
        tenant_id=tenant_id,
        entity_code=entity_code,
        threshold=threshold,
        limit=limit,
    )
    return [schemas.DuplicatePair(**r) for r in results]


@router.post("/entities/{entity_code}/anomalies", response_model=list[schemas.AnomalyResult])
def detect_anomalies(
    entity_code: str,
    z_score_threshold: float = Query(default=2.0, ge=0.5, le=5.0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[schemas.AnomalyResult]:
    results = service.detect_anomalies(
        db,
        tenant_id=tenant_id,
        entity_code=entity_code,
        z_score_threshold=z_score_threshold,
    )
    return [schemas.AnomalyResult(**r) for r in results]
