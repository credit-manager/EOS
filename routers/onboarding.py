"""
P52 Onboarding Router — Productization & SaaS Launch
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.onboarding_engine import OnboardingEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/onboarding", tags=["Onboarding"])


@router.get("/industries", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_industries(is_active: bool | None = None, db: Session=None):
    return {"status": "success", "data": OnboardingEngine(db).list_industry_templates(is_active=is_active)}


@router.get("/industries/{template_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_industry(template_id: str, db: Session=None):
    t = OnboardingEngine(db).get_industry_template(template_id)
    if not t:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Industry template not found"}})
    return {"status": "success", "data": t}


@router.get("/modules", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_modules(category: str | None = None, db: Session=None):
    return {"status": "success", "data": OnboardingEngine(db).list_module_definitions(category=category)}


@router.get("/modules/{module_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_module(module_id: str, db: Session=None):
    m = OnboardingEngine(db).get_module_definition(module_id)
    if not m:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Module definition not found"}})
    return {"status": "success", "data": m}


@router.post("/start", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def start_onboarding(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    tenant_id = user.get("tenant_id")
    engine = OnboardingEngine(db)
    existing = engine.get_onboarding(tenant_id)
    if existing and existing["status"] == "completed":
        raise HTTPException(400, detail={"status": "error", "error": {"code": "ALREADY_COMPLETED", "message": "Onboarding already completed"}})
    oid = engine.create_onboarding(
        tenant_id,
        admin_user_id=user.get("id") or body.get("admin_user_id"),
        admin_email=body.get("admin_email"),
    )
    db.commit()
    return {"status": "success", "data": {"id": oid, "current_step": "industry_selection", "status": "in_progress"}}


@router.get("/status", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_status(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": OnboardingEngine(db).get_onboarding_status(user.get("tenant_id"))}


@router.get("/current", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_current(user: dict | None=None, db: Session = Depends(get_db)):
    ob = OnboardingEngine(db).get_onboarding(user.get("tenant_id"))
    if not ob:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "No onboarding in progress"}})
    return {"status": "success", "data": ob}


@router.post("/complete-step", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def complete_step(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    step = body.get("step")
    data = body.get("data")
    if not step:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "step required"}})
    result = OnboardingEngine(db).complete_step(user.get("tenant_id"), step, data)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "STEP_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/list", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_onboardings(status: str | None = None, db: Session=None):
    return {"status": "success", "data": OnboardingEngine(db).list_onboardings(status=status)}
