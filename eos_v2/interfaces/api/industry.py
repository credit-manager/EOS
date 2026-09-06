from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from eos_v2.application.industry.pack_service import IndustryPackService
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission
from eos_v2.modules.industry.construction_real_estate import build_pack

router = APIRouter(prefix="/api/v1/industry", tags=["industry"])


@router.post("/packs/construction-real-estate/install")
def install_construction_real_estate(request: Request, identity=Depends(get_current_identity)) -> dict[str, object]:
    require_permission(identity, Permission.ADMIN)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        try:
            ids = IndustryPackService(SqlAlchemyMetadataRepository(session)).install(type("ConstructionPack", (), {"build": staticmethod(build_pack), "key": "construction-real-estate", "version": "1.0.0"})())
            session.commit()
        except (IntegrityError, ValueError) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"pack": "construction-real-estate", "version": "1.0.0", "entity_ids": [str(item) for item in ids]}
