"""
EOS Owner Control Plane API — /api/v1/control
Platform-level administration for EOS owners.
"""
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from core.auth import get_current_user, require_platform_owner
from core.module_registry import INDUSTRY_TEMPLATES as FRAMEWORK_TEMPLATES

router = APIRouter(prefix="/api/v1/control", tags=["EOS Control Plane"])


# ═══════════════════════════════════════════════════
# Platform Overview
# ═══════════════════════════════════════════════════

@router.get("/overview")
async def platform_overview(
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    """High-level platform metrics for the Control Center."""
    tenants = db.execute(text("SELECT COUNT(*) FROM dbp_saas_tenants")).fetchone()[0]
    active_tenants = db.execute(
        text("SELECT COUNT(*) FROM dbp_saas_tenants WHERE status = 'active'")
    ).fetchone()[0]
    companies = db.execute(text("SELECT COUNT(*) FROM dbp_companies")).fetchone()[0]
    users = db.execute(text("SELECT COUNT(*) FROM dbp_users WHERE is_active = true")).fetchone()[0]
    plans = db.execute(text("SELECT COUNT(*) FROM dbp_saas_plans WHERE is_active = true")).fetchone()[0]
    templates = db.execute(text("SELECT COUNT(*) FROM dbp_industry_templates WHERE is_active = true")).fetchone()[0]
    marketplace = db.execute(text("SELECT COUNT(*) FROM dbp_marketplace_items WHERE is_published = true")).fetchone()[0]
    audit_count = db.execute(text("SELECT COUNT(*) FROM dbp_audit_trail")).fetchone()[0]

    return {
        "tenants_total": tenants,
        "tenants_active": active_tenants,
        "companies_total": companies,
        "users_total": users,
        "plans_total": plans,
        "templates_total": templates,
        "marketplace_total": marketplace,
        "audit_entries": audit_count,
    }


# ═══════════════════════════════════════════════════
# Tenants
# ═══════════════════════════════════════════════════

@router.get("/tenants")
async def list_tenants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    if search:
        conditions.append("(t.name ILIKE :search OR t.slug ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_saas_tenants t WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT t.id, t.tenant_id, t.name, t.slug, t.status, t.plan_id, "
             f"p.plan_name, t.max_users, t.max_companies, t.created_at, t.updated_at "
             f"FROM dbp_saas_tenants t "
             f"LEFT JOIN dbp_saas_plans p ON t.plan_id = p.id "
             f"WHERE {where} ORDER BY t.created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()

    data = []
    for r in rows:
        data.append({
            "id": r[0], "tenant_id": r[1], "name": r[2], "slug": r[3],
            "status": r[4] or "active", "plan_id": r[5],
            "plan_name": r[6], "max_users": r[7], "max_companies": r[8],
            "created_at": r[9].isoformat() if r[9] else None,
            "updated_at": r[10].isoformat() if r[10] else None,
        })
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/tenants/{tenant_id}/info")
async def get_tenant_info(tenant_id: str, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    """Get tenant info including industry, company name, and installed modules."""
    rows = db.execute(
        text("SELECT item_code, status FROM dbp_tenant_installations WHERE tenant_id = :tid"),
        {"tid": tenant_id}
    ).fetchall()
    installed = {r[0] for r in rows if r[1] == 'installed'}

    industry = 'general'
    industry_name = 'General'
    for code, tmpl in FRAMEWORK_TEMPLATES.items():
        base = set(tmpl.get("base_modules", []))
        if base.issubset(installed):
            industry = code
            industry_name = tmpl.get("name", code)
            break

    company = db.execute(
        text("SELECT name_en, base_currency FROM dbp_companies WHERE tenant_id = :tid LIMIT 1"),
        {"tid": tenant_id}
    ).fetchone()

    return {
        "tenant_id": tenant_id,
        "industry": industry,
        "industry_name": industry_name,
        "company_name": company[0] if company else None,
        "currency": company[1] if company else "SAR",
        "modules": list(installed),
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    r = db.execute(
        text("SELECT t.id, t.tenant_id, t.name, t.slug, t.status, t.plan_id, "
             "p.plan_name, t.max_users, t.max_companies, t.settings, t.created_at, t.updated_at "
             "FROM dbp_saas_tenants t LEFT JOIN dbp_saas_plans p ON t.plan_id = p.id "
             "WHERE t.tenant_id = :tid"), {"tid": tenant_id}
    ).fetchone()
    if not r:
        raise HTTPException(404, detail="Tenant not found")

    company_count = db.execute(
        text("SELECT COUNT(*) FROM dbp_companies WHERE tenant_id = :tid"), {"tid": tenant_id}
    ).fetchone()[0]
    user_count = db.execute(
        text("SELECT COUNT(*) FROM dbp_users WHERE tenant_id = :tid AND is_active = true"), {"tid": tenant_id}
    ).fetchone()[0]

    return {
        "id": r[0], "tenant_id": r[1], "name": r[2], "slug": r[3],
        "status": r[4], "plan_id": r[5], "plan_name": r[6],
        "max_users": r[7], "max_companies": r[8],
        "settings": r[9],
        "company_count": company_count,
        "user_count": user_count,
        "created_at": r[10].isoformat() if r[10] else None,
        "updated_at": r[11].isoformat() if r[11] else None,
    }


@router.post("/tenants", status_code=201)
async def provision_tenant(body: dict, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    """
    Full tenant provisioning: Tenant → License → Admin User → Company → Template → Modules → Accounts.
    POST /api/v1/control/tenants
    Body: { name, industry_code, plan_id, admin_email, admin_password, admin_name, slug?, currency? }
    """
    name = str(body.get("name") or "").strip()
    industry_code = str(body.get("industry_code") or "").strip()
    admin_email = str(body.get("admin_email") or "").strip().lower()
    admin_password = body.get("admin_password")
    admin_name = str(body.get("admin_name") or "").strip()

    if not name:
        raise HTTPException(400, detail="name required")
    if not industry_code:
        raise HTTPException(400, detail="industry_code required (construction, trading, retail, restaurant, services, manufacturing)")
    if not admin_email:
        raise HTTPException(400, detail="admin_email required")
    if not isinstance(admin_password, str) or len(admin_password) < 12:
        raise HTTPException(400, detail="admin_password must be at least 12 characters")

    existing = db.execute(
        text("SELECT id FROM dbp_users WHERE email = :email"), {"email": admin_email}
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Email {admin_email} already registered")

    plan = None
    if body.get("plan_id"):
        plan = db.execute(
            text("SELECT id, plan_name, max_users, max_companies, max_storage_gb "
                 "FROM dbp_saas_plans WHERE id = :pid"), {"pid": body["plan_id"]}
        ).fetchone()

    template = db.execute(
        text("SELECT id, industry_code, industry_name, default_modules, default_settings, default_accounts "
             "FROM dbp_industry_templates WHERE industry_code = :code AND is_active = true"),
        {"code": industry_code}
    ).fetchone()
    if not template:
        raise HTTPException(400, detail=f"Industry template '{industry_code}' not found")

    now = datetime.now(timezone.utc)

    # ── Step 1: Create Tenant ──────────────────
    tid = str(uuid.uuid4())
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    slug = body.get("slug", name.lower().replace(" ", "-")[:30])
