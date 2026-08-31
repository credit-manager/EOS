"""
EOS Owner Control Plane API — /api/v1/control
Platform-level administration for EOS owners.
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

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
    # Get installed modules
    rows = db.execute(
        text("SELECT item_code, status FROM dbp_tenant_installations WHERE tenant_id = :tid"),
        {"tid": tenant_id}
    ).fetchall()
    installed = {r[0] for r in rows if r[1] == 'installed'}

    # Detect industry from framework templates
    industry = 'general'
    industry_name = 'General'
    for code, tmpl in FRAMEWORK_TEMPLATES.items():
        base = set(tmpl.get("base_modules", []))
        if base.issubset(installed):
            industry = code
            industry_name = tmpl.get("name", code)
            break

    # Get company info
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

    # Get related stats
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
    name = body.get("name")
    industry_code = body.get("industry_code")
    admin_email = body.get("admin_email")
    admin_password = body.get("admin_password", "admin123")
    admin_name = body.get("admin_name", "")

    if not name:
        raise HTTPException(400, detail="name required")
    if not industry_code:
        raise HTTPException(400, detail="industry_code required (construction, trading, retail, restaurant, services, manufacturing)")
    if not admin_email:
        raise HTTPException(400, detail="admin_email required")

    # Check email not taken
    existing = db.execute(
        text("SELECT id FROM dbp_users WHERE email = :email"), {"email": admin_email}
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Email {admin_email} already registered")

    # Fetch plan
    plan = None
    if body.get("plan_id"):
        plan = db.execute(
            text("SELECT id, plan_name, max_users, max_companies, max_storage_gb "
                 "FROM dbp_saas_plans WHERE id = :pid"), {"pid": body["plan_id"]}
        ).fetchone()

    # Fetch industry template
    template = db.execute(
        text("SELECT id, industry_code, industry_name, default_modules, default_settings, default_accounts "
             "FROM dbp_industry_templates WHERE industry_code = :code AND is_active = true"),
        {"code": industry_code}
    ).fetchone()
    if not template:
        raise HTTPException(400, detail=f"Industry template '{industry_code}' not found")

    now = datetime.now(timezone.utc)
    import json, hashlib

    # ── Step 1: Create Tenant ──────────────────
    tid = str(uuid.uuid4())
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    slug = body.get("slug", name.lower().replace(" ", "-")[:30])
    max_users = plan[2] if plan else 5
    max_companies = plan[3] if plan else 1

    db.execute(
        text("INSERT INTO dbp_saas_tenants (id, tenant_id, name, slug, status, plan_id, "
             "max_users, max_companies, settings, created_at, updated_at) "
             "VALUES (:id, :tid, :name, :slug, 'active', :plan, :mu, :mc, :settings, :now, :now)"),
        {"id": tid, "tid": tenant_id, "name": name, "slug": slug,
         "plan": body.get("plan_id"), "mu": max_users, "mc": max_companies,
         "settings": json.dumps(template[4] or {}), "now": now},
    )

    # ── Step 2: Create License ─────────────────
    license_id = str(uuid.uuid4())
    license_key = f"EOS-{tenant_id[-8:].upper()}-{uuid.uuid4().hex[:8].upper()}"
    db.execute(
        text("INSERT INTO dbp_licenses (id, tenant_id, license_key, license_type, max_seats, "
             "valid_from, valid_until, status, features, created_at, updated_at) "
             "VALUES (:id, :tid, :key, :type, :seats, :from, :until, 'active', :feat, :now, :now)"),
        {"id": license_id, "tid": tenant_id, "key": license_key,
         "type": plan[1] if plan else "starter",
         "seats": max_users, "from": now,
         "until": datetime(now.year + 1, now.month, now.day, tzinfo=timezone.utc),
         "feat": json.dumps(template[3] or {}), "now": now},
    )

    # ── Step 3: Create Admin User ───────────────
    user_id = str(uuid.uuid4())
    from passlib.hash import bcrypt as _bcrypt
    pw_hash = _bcrypt.hash(admin_password)
    first_name = admin_name.split()[0] if admin_name else "Admin"
    last_name = " ".join(admin_name.split()[1:]) if admin_name and len(admin_name.split()) > 1 else ""

    db.execute(
        text("INSERT INTO dbp_users (id, tenant_id, email, password_hash, first_name, last_name, "
             "role, is_active, email_verified, created_at, updated_at) "
             "VALUES (:id, :tid, :email, :pw, :fn, :ln, 'admin', true, true, :now, :now)"),
        {"id": user_id, "tid": tenant_id, "email": admin_email,
         "pw": pw_hash, "fn": first_name, "ln": last_name, "now": now},
    )

    # ── Step 4: Create Company ──────────────────
    company_id = str(uuid.uuid4())
    currency = body.get("currency", (template[4] or {}).get("base_currency", "SAR"))
    db.execute(
        text("INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar, country, "
             "base_currency, is_active, created_at) "
             "VALUES (:id, :tid, :code, :name, :name_ar, :country, :curr, true, :now)"),
        {"id": company_id, "tid": tenant_id, "code": slug[:30], "name": name,
         "name_ar": body.get("name_ar", name), "country": body.get("country", "Saudi Arabia"),
         "curr": currency, "now": now},
    )

    # ── Step 5: Apply Industry Template ─────────
    # Use framework module registry as primary source, DB template as fallback
    framework_tmpl = FRAMEWORK_TEMPLATES.get(industry_code, {})
    base_modules = framework_tmpl.get("base_modules", [])
    optional_modules = framework_tmpl.get("optional_modules", [])
    default_modules = base_modules + optional_modules

    # Also check DB template for any additional modules
    db_modules = template[3] or []
    if isinstance(db_modules, str):
        db_modules = json.loads(db_modules)
    if db_modules and not default_modules:
        default_modules = db_modules
    elif db_modules:
        # Merge: framework modules + DB modules (deduplicated)
        existing = set(default_modules)
        for m in db_modules:
            if m not in existing:
                default_modules.append(m)

    # Install modules via dbp_tenant_installations
    for module_code in default_modules:
        iid = str(uuid.uuid4())
        db.execute(
            text("INSERT INTO dbp_tenant_installations (id, tenant_id, item_code, status, applied_payload, installed_at) "
                 "VALUES (:id, :tid, :item, 'installed', '{}', :now)"),
            {"id": iid, "tid": tenant_id, "item": module_code, "now": now},
        )

    # ── Step 6: Create Default Chart of Accounts ─
    default_accounts = template[5] or []
    if isinstance(default_accounts, str):
        default_accounts = json.loads(default_accounts)

    for acct in default_accounts:
        acct_id = str(uuid.uuid4())
        db.execute(
            text("INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, "
                 "account_type, is_active, is_system, created_at) "
                 "VALUES (:id, :tid, :cid, :code, :name, :type, true, false, :now)"),
            {"id": acct_id, "tid": tenant_id, "cid": company_id,
             "code": acct.get("code", ""), "name": acct.get("name", ""),
             "type": acct.get("account_type", "asset"), "now": now},
        )

    db.commit()

    return {
        "message": "Tenant provisioned successfully",
        "tenant_id": tenant_id,
        "company_id": company_id,
        "license_key": license_key,
        "admin_email": admin_email,
        "admin_password": admin_password,
        "industry": template[1],
        "modules_enabled": default_modules,
        "accounts_created": len(default_accounts),
        "login_url": f"/login",
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, body: dict, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    existing = db.execute(
        text("SELECT id FROM dbp_saas_tenants WHERE tenant_id = :tid"), {"tid": tenant_id}
    ).fetchone()
    if not existing:
        raise HTTPException(404, detail="Tenant not found")

    fields, params = [], {"tid": tenant_id}
    for col in ("name", "status", "plan_id", "max_users", "max_companies"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        fields.append("updated_at = :now")
        params["now"] = datetime.now(timezone.utc)
        db.execute(text(f"UPDATE dbp_saas_tenants SET {', '.join(fields)} WHERE tenant_id = :tid"), params)
        db.commit()
    return {"message": "Tenant updated"}


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE dbp_saas_tenants SET status = 'suspended', updated_at = :now WHERE tenant_id = :tid"),
        {"tid": tenant_id, "now": datetime.now(timezone.utc)},
    )
    db.commit()
    return {"message": "Tenant suspended"}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(tenant_id: str, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE dbp_saas_tenants SET status = 'active', updated_at = :now WHERE tenant_id = :tid"),
        {"tid": tenant_id, "now": datetime.now(timezone.utc)},
    )
    db.commit()
    return {"message": "Tenant activated"}


@router.post("/tenants/{tenant_id}/impersonate")
async def impersonate_tenant(tenant_id: str, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    """
    Owner impersonates a tenant user for support.
    Returns a JWT scoped to the target tenant. All actions logged in audit.
    """
    # Verify tenant exists and is active
    tenant = db.execute(
        text("SELECT id, tenant_id, name, status FROM dbp_saas_tenants WHERE tenant_id = :tid"),
        {"tid": tenant_id}
    ).fetchone()
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")
    if tenant[3] != 'active':
        raise HTTPException(400, detail="Tenant is not active")

    # Find tenant admin user
    admin_user = db.execute(
        text("SELECT id, email, first_name, last_name FROM dbp_users "
             "WHERE tenant_id = :tid AND role = 'admin' AND is_active = true LIMIT 1"),
        {"tid": tenant_id}
    ).fetchone()

    if not admin_user:
        raise HTTPException(400, detail="No admin user found for this tenant")

    # Get tenant's industry from installations
    installations = db.execute(
        text("SELECT item_code FROM dbp_tenant_installations WHERE tenant_id = :tid LIMIT 1"),
        {"tid": tenant_id}
    ).fetchone()
    industry = installations[0] if installations else 'general'

    # Get company info
    company = db.execute(
        text("SELECT name_en, base_currency FROM dbp_companies WHERE tenant_id = :tid LIMIT 1"),
        {"tid": tenant_id}
    ).fetchone()

    # Create impersonation token (scoped to tenant)
    from core.auth import create_test_token
    token = create_test_token(tenant_id, admin_user[1])

    # Log impersonation in audit
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO dbp_audit_trail (id, tenant_id, entity_type, entity_id, action, "
             "actor_id, actor_email, actor_roles, ip_address, created_at) "
             "VALUES (:id, :tid, 'impersonate', :eid, 'login', :uid, :email, 'owner', '127.0.0.1', :now)"),
        {"id": str(uuid.uuid4()), "tid": tenant_id, "eid": admin_user[0],
         "uid": user.get("user_id", "owner"), "email": user.get("email", "owner@eos.com"), "now": now},
    )
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": tenant_id,
        "tenant_name": tenant[2],
        "industry": industry,
        "company_name": company[0] if company else tenant[2],
        "currency": company[1] if company else "SAR",
        "impersonated_user": admin_user[1],
        "message": "Impersonation token created — all actions will be logged",
    }


# ═══════════════════════════════════════════════════
# Plans
# ═══════════════════════════════════════════════════

@router.get("/plans")
async def list_plans(user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, plan_name, plan_code, price_monthly, price_yearly, "
             "max_users, max_companies, max_storage_gb, features, is_active, created_at "
             "FROM dbp_saas_plans ORDER BY price_monthly")
    ).fetchall()
    data = [{"id": r[0], "plan_name": r[1], "plan_code": r[2],
             "price_monthly": float(r[3]) if r[3] else 0,
             "price_yearly": float(r[4]) if r[4] else 0,
             "max_users": r[5], "max_companies": r[6],
             "max_storage_gb": r[7], "features": r[8],
             "is_active": r[9] if r[9] is not None else True,
             "created_at": r[10].isoformat() if r[10] else None}
            for r in rows]
    return {"data": data, "total": len(data)}


@router.post("/plans", status_code=201)
async def create_plan(body: dict, user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO dbp_saas_plans (id, tenant_id, plan_name, plan_code, price_monthly, "
             "price_yearly, max_users, max_companies, max_storage_gb, features, is_active, created_at, updated_at) "
             "VALUES (:id, :tid, :name, :code, :pm, :py, :mu, :mc, :ms, :feat, true, :now, :now)"),
        {"id": pid, "tid": "platform", "name": body.get("plan_name", ""),
         "code": body.get("plan_code", ""), "pm": body.get("price_monthly", 0),
         "py": body.get("price_yearly", 0), "mu": body.get("max_users", 5),
         "mc": body.get("max_companies", 1), "ms": body.get("max_storage_gb", 1),
         "feat": body.get("features"), "now": now},
    )
    db.commit()
    return {"id": pid, "message": "Plan created"}


# ═══════════════════════════════════════════════════
# Industry Templates
# ═══════════════════════════════════════════════════

@router.get("/templates")
async def list_templates(user: dict = Depends(require_platform_owner), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, industry_code, industry_name, industry_name_ar, description, "
             "default_modules, is_active, sort_order "
             "FROM dbp_industry_templates ORDER BY sort_order")
    ).fetchall()
    data = [{"id": r[0], "industry_code": r[1], "industry_name": r[2],
             "industry_name_ar": r[3], "description": r[4],
             "default_modules": r[5],
             "is_active": r[6] if r[6] is not None else True,
             "sort_order": r[7]}
            for r in rows]
    return {"data": data, "total": len(data)}


# ═══════════════════════════════════════════════════
# Marketplace
# ═══════════════════════════════════════════════════

@router.get("/marketplace")
async def list_marketplace(
    item_type: Optional[str] = None,
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    conditions = ["is_published = true"]
    params: dict = {}
    if item_type:
        conditions.append("item_type = :type")
        params["type"] = item_type
    where = " AND ".join(conditions)

    rows = db.execute(
        text(f"SELECT id, item_code, item_type, name_en, name_ar, description, publisher, "
             f"version, is_featured, is_free, price_monthly, created_at "
             f"FROM dbp_marketplace_items WHERE {where} ORDER BY is_featured DESC, name_en"),
        params,
    ).fetchall()
    data = [{"id": r[0], "item_code": r[1], "item_type": r[2],
             "name": r[3], "name_ar": r[4], "description": r[5],
             "publisher": r[6], "version": r[7],
             "is_featured": r[8] or False, "is_free": r[9] or False,
             "price_monthly": float(r[10]) if r[10] else 0,
             "created_at": r[11].isoformat() if r[11] else None}
            for r in rows]
    return {"data": data, "total": len(data)}


# ═══════════════════════════════════════════════════
# Audit Trail
# ═══════════════════════════════════════════════════

@router.get("/audit")
async def list_audit(
    tenant_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if tenant_id:
        conditions.append("tenant_id = :tid")
        params["tid"] = tenant_id
    if entity_type:
        conditions.append("entity_type = :et")
        params["et"] = entity_type
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_audit_trail WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT id, tenant_id, entity_type, entity_id, action, actor_email, "
             f"old_values, new_values, ip_address, created_at "
             f"FROM dbp_audit_trail WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "tenant_id": r[1], "entity_type": r[2], "entity_id": r[3],
             "action": r[4], "actor_email": r[5],
             "old_values": r[6], "new_values": r[7],
             "ip_address": r[8],
             "created_at": r[9].isoformat() if r[9] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


# ═══════════════════════════════════════════════════
# Licenses
# ═══════════════════════════════════════════════════

@router.get("/licenses")
async def list_licenses(
    tenant_id: Optional[str] = None,
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if tenant_id:
        conditions.append("tenant_id = :tid")
        params["tid"] = tenant_id
    where = " AND ".join(conditions)

    rows = db.execute(
        text(f"SELECT id, tenant_id, license_key, license_type, max_seats, "
             f"valid_from, valid_until, status, features, created_at "
             f"FROM dbp_licenses WHERE {where} ORDER BY created_at DESC"),
        params,
    ).fetchall()
    data = [{"id": r[0], "tenant_id": r[1], "license_key": r[2],
             "license_type": r[3], "max_seats": r[4],
             "valid_from": r[5].isoformat() if r[5] else None,
             "valid_until": r[6].isoformat() if r[6] else None,
             "status": r[7] or "active", "features": r[8],
             "created_at": r[9].isoformat() if r[9] else None}
            for r in rows]
    return {"data": data, "total": len(data)}


# ═══════════════════════════════════════════════════
# Companies (all tenants)
# ═══════════════════════════════════════════════════

@router.get("/companies")
async def list_all_companies(
    tenant_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_platform_owner),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if tenant_id:
        conditions.append("c.tenant_id = :tid")
        params["tid"] = tenant_id
    if search:
        conditions.append("(c.name_en ILIKE :search OR c.name_ar ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_companies c WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT c.id, c.tenant_id, c.code, c.name_en, c.name_ar, c.country, "
             f"c.base_currency, t.name as tenant_name "
             f"FROM dbp_companies c "
             f"LEFT JOIN dbp_saas_tenants t ON c.tenant_id = t.tenant_id "
             f"WHERE {where} ORDER BY c.name_en LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "tenant_id": r[1], "code": r[2],
             "name": r[3], "name_ar": r[4], "country": r[5],
             "currency": r[6] or "SAR", "tenant_name": r[7]}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}
