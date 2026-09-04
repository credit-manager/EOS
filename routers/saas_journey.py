"""
P58 SaaS Journey Router — the product's front door
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.saas_journey import SaaSJourneyEngine
from database import get_db


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


router = APIRouter(prefix="/api/v1/dynamic/experience", tags=["SaaS Experience"])


@router.post("/journeys", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def start(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSJourneyEngine(db).start_journey(
        user.get("tenant_id"), user.get("id") or "user",
        body.get("business_description"),
        company_name=body.get("company_name"),
        admin_email=body.get("admin_email"))
    if not result.get("success"):
        raise _err(400, "START_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": result}


@router.get("/journeys", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_journeys(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": SaaSJourneyEngine(db).list_journeys(user.get("tenant_id"))}


@router.get("/journeys/{jid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_journey(jid: str, user: dict | None=None, db: Session = Depends(get_db)):
    j = SaaSJourneyEngine(db).get_journey(user.get("tenant_id"), jid)
    if not j:
        raise _err(404, "NOT_FOUND", "Journey not found")
    return {"status": "success", "data": j}


@router.put("/journeys/{jid}/customize", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def customize(jid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSJourneyEngine(db).customize(user.get("tenant_id"), jid, body)
    if not result.get("success"):
        raise _err(400, "CUSTOMIZE_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.get("/journeys/{jid}/preview", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def preview(jid: str, user: dict | None=None, db: Session = Depends(get_db)):
    p = SaaSJourneyEngine(db).preview(user.get("tenant_id"), jid)
    if not p:
        raise _err(404, "NOT_FOUND", "Journey or draft not found")
    return {"status": "success", "data": p}


@router.post("/journeys/{jid}/select-plan", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def select_plan(jid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("plan_code"):
        raise _err(400, "MISSING", "plan_code required")
    result = SaaSJourneyEngine(db).select_plan(
        user.get("tenant_id"), jid, body["plan_code"],
        billing_cycle=body.get("billing_cycle", "monthly"))
    if not result.get("success"):
        raise _err(400, "PLAN_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.post("/journeys/{jid}/pay", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def pay(jid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSJourneyEngine(db).pay(user.get("tenant_id"), jid,
                                        payment_method=body.get("payment_method", "card"))
    if not result.get("success"):
        raise _err(400, "PAY_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.post("/journeys/{jid}/launch", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def launch(jid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSJourneyEngine(db).launch(user.get("tenant_id"), jid,
                                           confirmed=bool(body.get("confirmed")))
    if not result.get("success"):
        code = result.get("code", "LAUNCH_FAILED")
        raise HTTPException(400, detail={"status": "error", "error": {
            "code": code, "message": result["error"],
            "details": result.get("validation")}})
    return {"status": "success", "data": result}
