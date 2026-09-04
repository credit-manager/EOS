"""
P34 API Rate Limiting & Quotas Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.api_quota_engine import APIQuotaEngine
from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["API Quotas & Rate Limiting"])


# ── API Keys ───────────────────────────────────────────────────

@router.get("/companies/{cid}/api-keys",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_api_keys(cid: str, user: dict | None=None,
                        db: Session = Depends(get_db)):
    data = APIQuotaEngine(db).list_api_keys(user["tenant_id"], cid)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/api-keys",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_api_key(cid: str, body: dict,
                         user: dict | None=None,
                         db: Session = Depends(get_db)):
    if "name" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "name required"}})
    result = APIQuotaEngine(db).create_api_key(
        user["tenant_id"], cid, body["name"],
        permissions=body.get("permissions"),
        rate_limit_read=body.get("rate_limit_read", 200),
        rate_limit_write=body.get("rate_limit_write", 50))
    db.commit()
    return {"status": "success", "data": result}


@router.post("/api-keys/{kid}/revoke",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def revoke_api_key(kid: str, db: Session = Depends(get_db)):
    result = APIQuotaEngine(db).revoke_api_key(kid)
    if not result["success"]:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "API key not found"}})
    db.commit()
    return {"status": "success", "data": result}


# ── Usage Logs ─────────────────────────────────────────────────

@router.get("/api-usage",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_api_usage(api_key_id: str | None = None, from_date: str | None = None,
                        to_date: str | None = None,
                        user: dict | None=None,
                        db: Session = Depends(get_db)):
    engine = APIQuotaEngine(db)
    data = engine.get_usage_stats(
        user["tenant_id"], api_key_id=api_key_id,
        from_date=from_date, to_date=to_date)
    return {"status": "success", "data": data}


@router.get("/api-usage/stats",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_usage_stats(api_key_id: str | None = None, from_date: str | None = None,
                          to_date: str | None = None,
                          user: dict | None=None,
                          db: Session = Depends(get_db)):
    data = APIQuotaEngine(db).get_usage_stats(
        user["tenant_id"], api_key_id=api_key_id,
        from_date=from_date, to_date=to_date)
    return {"status": "success", "data": data}


# ── Rate Limit Rules ───────────────────────────────────────────

@router.get("/companies/{cid}/rate-limit-rules",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_rate_limit_rules(cid: str,
                                user: dict | None=None,
                                db: Session = Depends(get_db)):
    data = APIQuotaEngine(db).list_rate_limit_rules(user["tenant_id"], cid)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/rate-limit-rules",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_rate_limit_rule(cid: str, body: dict,
                                 user: dict | None=None,
                                 db: Session = Depends(get_db)):
    for field in ("endpoint_pattern", "method", "rate_limit"):
        if field not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{field} required"}})
    rid = APIQuotaEngine(db).create_rate_limit_rule(
        user["tenant_id"], cid, body["endpoint_pattern"],
        body["method"], body["rate_limit"],
        window_seconds=body.get("window_seconds", 60))
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.post("/check-rate-limit",
             dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def check_rate_limit(body: dict,
                           user: dict | None=None,
                           db: Session = Depends(get_db)):
    for field in ("endpoint", "method"):
        if field not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{field} required"}})
    data = APIQuotaEngine(db).check_rate_limit(
        user["tenant_id"], body["endpoint"], body["method"])
    return {"status": "success", "data": data}
