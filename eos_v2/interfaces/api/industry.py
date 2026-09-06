from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.application.audit.service import record_event
from eos_v2.application.industry.pack_catalog import CATALOG, get_pack
from eos_v2.application.industry.pack_service import IndustryPackService
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission

router = APIRouter(prefix="/api/v1/industry", tags=["industry"])


@router.get("/packs")
def list_packs(identity=Depends(get_current_identity)) -> dict[str, object]:
    require_permission(identity, Permission.READ)
    return {
        "packs": [
            {"key": pack.key, "version": pack.version, "display_name": pack.display_name}
            for pack in CATALOG
        ]
    }


@router.post("/packs/{pack_key}/install")
def install_pack(pack_key: str, request: Request, identity=Depends(get_current_identity)) -> dict[str, object]:
    require_permission(identity, Permission.ADMIN)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        pack = get_pack(pack_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Industry pack not found") from exc
    with database.session() as session:
        try:
            ids = IndustryPackService(SqlAlchemyMetadataRepository(session)).install(pack)
            record_event(
                session,
                action="industry_pack.installed",
                resource_type="industry_pack",
                resource_id=pack.key,
                actor_id=identity.actor.id,
                request_id=request.headers.get("X-Request-ID"),
                metadata={"version": pack.version, "entity_count": len(ids)},
            )
            session.commit()
        except (IntegrityError, ValueError) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"pack": pack.key, "version": pack.version, "entity_ids": [str(item) for item in ids]}
