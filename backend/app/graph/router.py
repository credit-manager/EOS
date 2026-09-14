from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .schemas import GraphStory
from .service import build_story

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/{entity_code}/{record_id}", response_model=GraphStory)
def get_story(
    entity_code: str,
    record_id: UUID,
    request: Request,
    depth: int = Query(default=2, ge=1, le=3),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GraphStory:
    return GraphStory(
        **build_story(
            db,
            tenant_id=tenant_id,
            role=request.state.role,
            entity_code=entity_code,
            record_id=record_id,
            depth=depth,
        )
    )
