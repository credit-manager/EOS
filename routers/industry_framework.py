"""EOS Industry Framework API with strict tenant authorization."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.module_registry import (
    INDUSTRY_TEMPLATES,
    MODULE_REGISTRY,
    build_dashboard_widgets,
    build_sidebar_menu,
)
from database import get_db
from security.tenant_scope import require_tenant_access

router = APIRouter(prefix="/api/v1/framework", tags=["Industry Framework"])

def _now(): return datetime.now(timezone.utc)
def _scope(user, tenant_id): return require_tenant_access(user, tenant_id)

def _detect_industry(installed):
    for code, tmpl in INDUSTRY_TEMPLATES.items():
        base = set(tmpl.get("base_modules", []))
        if base.issubset(installed):
            return {"industry": code, "name": tmpl["name"], "name_ar": tmpl["name_ar"],
                    "matched_modules": len(base & installed), "total_modules": len(base)}
    return {"industry": "general", "name": "General", "name_ar": "عام", "matched_modules": 0, "total_modules": 0}

@router.get("/modules")
async def list_modules(user: dict | None=None):
    return {"data": [{"code": c, "name": m["name"], "name_ar": m["name_ar"], "category": m["category"], "icon": m["icon"], "description": m["description"], "capabilities": m.get("capabilities", []), "dependencies": m.get("dependencies", [])} for c, m in MODULE_REGISTRY.items()], "total": len(MODULE_REGISTRY)}

@router.get("/modules/{module_code}")
async def get_module_detail(module_code: str, user: dict | None=None):
    mod = MODULE_REGISTRY.get(module_code)
    if not mod: raise HTTPException(404, detail=f"Module '{module_code}' not found")
    return {"code": module_code, **mod}

@router.get("/industries")
async def list_industries(user: dict | None=None):
    return {"data": [{"code": c, "name": t["name"], "name_ar": t["name_ar"], "description": t["description"], "modules_count": len(t.get("base_modules", []) + t.get("optional_modules", [])), "modules": t.get("base_modules", []) + t.get("optional_modules", [])} for c, t in INDUSTRY_TEMPLATES.items()], "total": len(INDUSTRY_TEMPLATES)}

@router.get("/industries/{industry_code}")
async def get_industry_detail(industry_code: str, user: dict | None=None):
    tmpl = INDUSTRY_TEMPLATES.get(industry_code)
    if not tmpl: raise HTTPException(404, detail=f"Industry '{industry_code}' not found")
    def details(codes):
        return [{"code": c, "name": MODULE_REGISTRY.get(c, {}).get("name", c), "name_ar": MODULE_REGISTRY.get(c, {}).get("name_ar", c), "category": MODULE_REGISTRY.get(c, {}).get("category", "core"), "icon": MODULE_REGISTRY.get(c, {}).get("icon", "AppstoreOutlined")} for c in codes]
    return {"code": industry_code, "name": tmpl["name"], "name_ar": tmpl["name_ar"], "description": tmpl["description"], "base_modules": details(tmpl.get("base_modules", [])), "optional_modules": details(tmpl.get("optional_modules", [])), "settings": tmpl.get("default_settings", {})}

@router.get("/tenants/{tenant_id}/modules")
async def get_tenant_modules(tenant_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    rows = db.execute(text("SELECT item_code, status, installed_at FROM dbp_tenant_installations WHERE tenant_id = :tid ORDER BY installed_at"), {"tid": tenant_id}).fetchall()
    modules = []
    for r in rows:
        mod = MODULE_REGISTRY.get(r[0], {})
        modules.append({"code": r[0], "name": mod.get("name", r[0]), "name_ar": mod.get("name_ar", r[0]), "category": mod.get("category", "core"), "icon": mod.get("icon", "AppstoreOutlined"), "status": r[1], "installed_at": r[2].isoformat() if r[2] else None})
    industry = _detect_industry({r[0] for r in rows})
    return {"tenant_id": tenant_id, **industry, "modules": modules, "total": len(modules)}

@router.get("/tenants/{tenant_id}/menu")
async def get_tenant_menu(tenant_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    rows = db.execute(text("SELECT item_code FROM dbp_tenant_installations WHERE tenant_id = :tid AND status = 'installed'"), {"tid": tenant_id}).fetchall()
    codes = [r[0] for r in rows]
    return {"menu": build_sidebar_menu(codes), "modules": codes}

@router.get("/tenants/{tenant_id}/dashboard-config")
async def get_tenant_dashboard_config(tenant_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    rows = db.execute(text("SELECT item_code FROM dbp_tenant_installations WHERE tenant_id = :tid AND status = 'installed'"), {"tid": tenant_id}).fetchall()
    codes = [r[0] for r in rows]
    return {"widgets": build_dashboard_widgets(codes), "modules": codes}

@router.post("/tenants/{tenant_id}/modules/{module_code}/enable")
async def enable_module(tenant_id: str, module_code: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    if module_code not in MODULE_REGISTRY: raise HTTPException(404, detail=f"Module '{module_code}' not found")
    existing = db.execute(text("SELECT id FROM dbp_tenant_installations WHERE tenant_id = :tid AND item_code = :mc"), {"tid": tenant_id, "mc": module_code}).fetchone()
    if existing:
        db.execute(text("UPDATE dbp_tenant_installations SET status = 'installed' WHERE tenant_id = :tid AND item_code = :mc"), {"tid": tenant_id, "mc": module_code})
    else:
        db.execute(text("INSERT INTO dbp_tenant_installations (id, tenant_id, item_code, status, applied_payload, installed_at) VALUES (:id, :tid, :mc, 'installed', '{}', :now)"), {"id": str(uuid.uuid4()), "tid": tenant_id, "mc": module_code, "now": _now()})
    db.commit(); return {"message": f"Module '{module_code}' enabled"}

@router.post("/tenants/{tenant_id}/modules/{module_code}/disable")
async def disable_module(tenant_id: str, module_code: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    db.execute(text("UPDATE dbp_tenant_installations SET status = 'disabled' WHERE tenant_id = :tid AND item_code = :mc"), {"tid": tenant_id, "mc": module_code})
    db.commit(); return {"message": f"Module '{module_code}' disabled"}

@router.get("/tenants/{tenant_id}/industry")
async def get_tenant_industry(tenant_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    _scope(user, tenant_id)
    rows = db.execute(text("SELECT item_code FROM dbp_tenant_installations WHERE tenant_id = :tid"), {"tid": tenant_id}).fetchall()
    return _detect_industry({r[0] for r in rows})
