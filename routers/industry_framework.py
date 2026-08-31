"""
EOS Industry Framework API — /api/v1/framework
Module registry, industry templates, tenant module management.
"""
import uuid
from typing import Optional, List
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import get_current_user
from core.module_registry import (
    MODULE_REGISTRY, INDUSTRY_TEMPLATES,
    get_module, get_industry_modules, get_industry_template,
    get_all_modules, get_all_industries,
    build_sidebar_menu, build_dashboard_widgets,
)

router = APIRouter(prefix="/api/v1/framework", tags=["Industry Framework"])


def _now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════
# Module Registry
# ═══════════════════════════════════════════════════

@router.get("/modules")
async def list_modules(user: dict = Depends(get_current_user)):
    """List all registered modules."""
    modules = []
    for code, mod in MODULE_REGISTRY.items():
        modules.append({
            "code": code,
            "name": mod["name"],
            "name_ar": mod["name_ar"],
            "category": mod["category"],
            "icon": mod["icon"],
            "description": mod["description"],
            "capabilities": mod.get("capabilities", []),
            "dependencies": mod.get("dependencies", []),
        })
    return {"data": modules, "total": len(modules)}


@router.get("/modules/{module_code}")
async def get_module_detail(module_code: str, user: dict = Depends(get_current_user)):
    """Get detailed module definition."""
    mod = MODULE_REGISTRY.get(module_code)
    if not mod:
        raise HTTPException(404, detail=f"Module '{module_code}' not found")
    return {"code": module_code, **mod}


# ═══════════════════════════════════════════════════
# Industry Templates
# ═══════════════════════════════════════════════════

@router.get("/industries")
async def list_industries(user: dict = Depends(get_current_user)):
    """List all industry templates."""
    industries = []
    for code, tmpl in INDUSTRY_TEMPLATES.items():
        modules = tmpl.get("base_modules", []) + tmpl.get("optional_modules", [])
        industries.append({
            "code": code,
            "name": tmpl["name"],
            "name_ar": tmpl["name_ar"],
            "description": tmpl["description"],
            "modules_count": len(modules),
            "modules": modules,
        })
    return {"data": industries, "total": len(industries)}


@router.get("/industries/{industry_code}")
async def get_industry_detail(industry_code: str, user: dict = Depends(get_current_user)):
    """Get industry template with full module details."""
    tmpl = INDUSTRY_TEMPLATES.get(industry_code)
    if not tmpl:
        raise HTTPException(404, detail=f"Industry '{industry_code}' not found")

    base = tmpl.get("base_modules", [])
    optional = tmpl.get("optional_modules", [])

    # Enrich with module details
    base_details = []
    for code in base:
        mod = MODULE_REGISTRY.get(code, {})
        base_details.append({
            "code": code,
            "name": mod.get("name", code),
            "name_ar": mod.get("name_ar", code),
            "category": mod.get("category", "core"),
            "icon": mod.get("icon", "AppstoreOutlined"),
        })

    optional_details = []
    for code in optional:
        mod = MODULE_REGISTRY.get(code, {})
        optional_details.append({
            "code": code,
            "name": mod.get("name", code),
            "name_ar": mod.get("name_ar", code),
        })

    return {
        "code": industry_code,
        "name": tmpl["name"],
        "name_ar": tmpl["name_ar"],
        "description": tmpl["description"],
        "base_modules": base_details,
        "optional_modules": optional_details,
        "settings": tmpl.get("default_settings", {}),
    }


# ═══════════════════════════════════════════════════
# Tenant Modules — manage which modules are enabled
# ═══════════════════════════════════════════════════

@router.get("/tenants/{tenant_id}/modules")
async def get_tenant_modules(tenant_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get list of enabled modules for a tenant."""
    rows = db.execute(
        text("SELECT item_code, status, installed_at FROM dbp_tenant_installations "
             "WHERE tenant_id = :tid ORDER BY installed_at"),
        {"tid": tenant_id}
    ).fetchall()

    modules = []
    for r in rows:
        mod = MODULE_REGISTRY.get(r[0], {})
        modules.append({
            "code": r[0],
            "name": mod.get("name", r[0]),
            "name_ar": mod.get("name_ar", r[0]),
            "category": mod.get("category", "core"),
            "icon": mod.get("icon", "AppstoreOutlined"),
            "status": r[1],
            "installed_at": r[2].isoformat() if r[2] else None,
        })

    # Get industry
    inst = db.execute(
        text("SELECT item_code FROM dbp_tenant_installations "
             "WHERE tenant_id = :tid AND item_code IN :inds LIMIT 1"),
        {"tid": tenant_id, "inds": tuple(INDUSTRY_TEMPLATES.keys())}
    ).fetchone()
    industry = inst[0] if inst else "general"

    return {
        "tenant_id": tenant_id,
        "industry": industry,
        "modules": modules,
        "total": len(modules),
    }


@router.get("/tenants/{tenant_id}/menu")
async def get_tenant_menu(tenant_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get sidebar menu for a tenant based on enabled modules."""
    rows = db.execute(
        text("SELECT item_code FROM dbp_tenant_installations "
             "WHERE tenant_id = :tid AND status = 'installed'"),
        {"tid": tenant_id}
    ).fetchall()
    module_codes = [r[0] for r in rows]

    menu = build_sidebar_menu(module_codes)
    return {"menu": menu, "modules": module_codes}


@router.get("/tenants/{tenant_id}/dashboard-config")
async def get_tenant_dashboard_config(tenant_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get dashboard widget configuration for a tenant."""
    rows = db.execute(
        text("SELECT item_code FROM dbp_tenant_installations "
             "WHERE tenant_id = :tid AND status = 'installed'"),
        {"tid": tenant_id}
    ).fetchall()
    module_codes = [r[0] for r in rows]

    widgets = build_dashboard_widgets(module_codes)
    return {"widgets": widgets, "modules": module_codes}


@router.post("/tenants/{tenant_id}/modules/{module_code}/enable")
async def enable_module(tenant_id: str, module_code: str,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enable a module for a tenant."""
    if module_code not in MODULE_REGISTRY:
        raise HTTPException(404, detail=f"Module '{module_code}' not found")

    # Check if already installed
    existing = db.execute(
        text("SELECT id FROM dbp_tenant_installations "
             "WHERE tenant_id = :tid AND item_code = :mc"),
        {"tid": tenant_id, "mc": module_code}
    ).fetchone()

    if existing:
        # Re-enable if disabled
        db.execute(
            text("UPDATE dbp_tenant_installations SET status = 'installed' "
                 "WHERE tenant_id = :tid AND item_code = :mc"),
            {"tid": tenant_id, "mc": module_code}
        )
    else:
        iid = str(uuid.uuid4())
        db.execute(
            text("INSERT INTO dbp_tenant_installations (id, tenant_id, item_code, status, applied_payload, installed_at) "
                 "VALUES (:id, :tid, :mc, 'installed', '{}', :now)"),
            {"id": iid, "tid": tenant_id, "mc": module_code, "now": _now()},
        )

    db.commit()
    return {"message": f"Module '{module_code}' enabled"}


@router.post("/tenants/{tenant_id}/modules/{module_code}/disable")
async def disable_module(tenant_id: str, module_code: str,
                         user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disable a module for a tenant."""
    db.execute(
        text("UPDATE dbp_tenant_installations SET status = 'disabled' "
             "WHERE tenant_id = :tid AND item_code = :mc"),
        {"tid": tenant_id, "mc": module_code}
    )
    db.commit()
    return {"message": f"Module '{module_code}' disabled"}


# ═══════════════════════════════════════════════════
# Tenant Industry Detection
# ═══════════════════════════════════════════════════

@router.get("/tenants/{tenant_id}/industry")
async def get_tenant_industry(tenant_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Detect tenant industry from installed modules."""
    rows = db.execute(
        text("SELECT item_code FROM dbp_tenant_installations WHERE tenant_id = :tid"),
        {"tid": tenant_id}
    ).fetchall()
    installed = {r[0] for r in rows}

    # Match against industry templates
    for code, tmpl in INDUSTRY_TEMPLATES.items():
        base = set(tmpl.get("base_modules", []))
        if base.issubset(installed):
            return {
                "industry": code,
                "name": tmpl["name"],
                "name_ar": tmpl["name_ar"],
                "matched_modules": len(base & installed),
                "total_modules": len(base),
            }

    return {"industry": "general", "name": "General", "name_ar": "عام"}
