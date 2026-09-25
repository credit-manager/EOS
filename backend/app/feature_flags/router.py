"""Feature Flags admin API."""
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth.security import Principal, require_principal
from .models import FeatureFlag

router = APIRouter(prefix="/api/v1/admin/feature-flags", tags=["admin-feature-flags"])


def require_super_admin(principal: Principal = Depends(require_principal)):
    if principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return principal


@router.get("")
def list_flags(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    flags = db.execute(select(FeatureFlag).order_by(FeatureFlag.code)).scalars().all()
    result = []
    for f in flags:
        result.append({
            "id": f.id,
            "code": f.code,
            "name": f.name,
            "description": f.description or "",
            "isGlobal": f.is_global,
            "enabledPlans": json.loads(f.enabled_plans) if f.enabled_plans else [],
            "enabledTenants": json.loads(f.enabled_tenants) if f.enabled_tenants else [],
            "isActive": f.is_active,
            "createdAt": f.created_at.isoformat() if f.created_at else "",
        })
    return {"flags": result}


@router.post("")
def create_flag(
    data: dict,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    flag = FeatureFlag(
        id=str(uuid4()),
        code=data.get("code", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        is_global=data.get("isGlobal", False),
        enabled_plans=json.dumps(data.get("enabledPlans", [])),
        enabled_tenants=json.dumps(data.get("enabledTenants", [])),
        is_active=data.get("isActive", True),
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return {"id": flag.id, "status": "created"}


@router.patch("/{flag_id}")
def update_flag(
    flag_id: str,
    data: dict,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    if "name" in data:
        flag.name = data["name"]
    if "description" in data:
        flag.description = data["description"]
    if "isGlobal" in data:
        flag.is_global = data["isGlobal"]
    if "enabledPlans" in data:
        flag.enabled_plans = json.dumps(data["enabledPlans"])
    if "enabledTenants" in data:
        flag.enabled_tenants = json.dumps(data["enabledTenants"])
    if "isActive" in data:
        flag.is_active = data["isActive"]
    db.commit()
    db.refresh(flag)
    return {"id": flag.id, "status": "updated"}


@router.delete("/{flag_id}")
def delete_flag(
    flag_id: str,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    flag = db.get(FeatureFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    db.delete(flag)
    db.commit()
    return {"status": "deleted"}
