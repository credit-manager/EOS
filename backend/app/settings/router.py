from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .models import TenantSettings
from .schemas import TenantSettingsResponse, TenantSettingsUpdate

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _get_or_create(db: Session, tenant_id) -> TenantSettings:
    tid = str(tenant_id)
    obj = db.query(TenantSettings).filter(TenantSettings.tenant_id == tid).first()
    if not obj:
        obj = TenantSettings(tenant_id=tid)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


@router.get("", response_model=TenantSettingsResponse)
def get_settings(
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return _get_or_create(db, tenant_id)


@router.patch("", response_model=TenantSettingsResponse)
def update_settings(
    payload: TenantSettingsUpdate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = _get_or_create(db, tenant_id)
    data = payload.model_dump(exclude_unset=True)

    if "notifications" in data and data["notifications"] is not None:
        existing = obj.notifications or {}
        existing.update(data["notifications"].model_dump())
        data["notifications"] = existing

    if "appearance" in data and data["appearance"] is not None:
        existing = obj.appearance or {}
        existing.update(data["appearance"].model_dump())
        data["appearance"] = existing

    if "security" in data and data["security"] is not None:
        existing = obj.security or {}
        existing.update(data["security"].model_dump())
        data["security"] = existing

    for k, v in data.items():
        if v is not None:
            setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return obj
