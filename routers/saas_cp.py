from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.saas_cp_engine import SaaSCPEngine
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/saas", tags=["SaaS Control Plane"])


# ------------------------------------------------------------ saas tenants
@router.get("/tenants",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_tenants(status: str | None = None,
                      user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).list_tenants(status=status)
    return {"status": "success", "data": data}


@router.post("/tenants",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_tenant(body: dict,
                       user: dict | None=None, db: Session = Depends(get_db)):
    required = ["tenant_id", "name", "slug"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    tid = SaaSCPEngine(db).create_tenant(
        body["tenant_id"], body["name"], body["slug"],
        plan_id=body.get("plan_id"), max_users=body.get("max_users", 10),
        max_companies=body.get("max_companies", 1),
        settings=body.get("settings"))
    db.commit()
    return {"status": "success", "data": {"id": tid, "message": "Tenant created"}}


@router.get("/tenants/{tenant_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_tenant(tenant_id: str,
                    user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).get_tenant(tenant_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    return {"status": "success", "data": data}


@router.put("/tenants/{tenant_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_tenant(tenant_id: str, body: dict,
                       user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSCPEngine(db).update_tenant(
        tenant_id, name=body.get("name"), status=body.get("status"),
        plan_id=body.get("plan_id"), max_users=body.get("max_users"),
        max_companies=body.get("max_companies"), settings=body.get("settings"))
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------------------- saas plans
@router.get("/plans",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_plans(user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).list_plans(user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/plans",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_plan(body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    required = ["plan_name", "plan_code"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = SaaSCPEngine(db).create_plan(
        user["tenant_id"], body["plan_name"], body["plan_code"],
        price_monthly=body.get("price_monthly", 0),
        price_yearly=body.get("price_yearly", 0),
        max_users=body.get("max_users", 10),
        max_companies=body.get("max_companies", 1),
        max_storage_gb=body.get("max_storage_gb", 5),
        features=body.get("features"))
    db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Plan created"}}


@router.get("/plans/{plan_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_plan(plan_id: str,
                  user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).get_plan(user["tenant_id"], plan_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Plan not found"}})
    return {"status": "success", "data": data}


@router.put("/plans/{plan_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_plan(plan_id: str, body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSCPEngine(db).update_plan(
        user["tenant_id"], plan_id,
        is_active=body.get("is_active"),
        price_monthly=body.get("price_monthly"),
        price_yearly=body.get("price_yearly"))
    db.commit()
    return {"status": "success", "data": result}


# ----------------------------------------------------------- saas features
@router.get("/features",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_features(category: str | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).list_features(category=category)
    return {"status": "success", "data": data}


@router.post("/features",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_feature(body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    required = ["feature_name", "feature_code"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = SaaSCPEngine(db).create_feature(
        body["feature_name"], body["feature_code"],
        description=body.get("description"), category=body.get("category"),
        is_default=body.get("is_default", False))
    db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Feature created"}}


@router.get("/features/{feature_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_feature(feature_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).get_feature(feature_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Feature not found"}})
    return {"status": "success", "data": data}


# ----------------------------------------------------- tenant features
@router.post("/tenants/{tenant_id}/features",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def enable_feature(tenant_id: str, body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    required = ["feature_id"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = SaaSCPEngine(db).enable_tenant_feature(
        tenant_id, body["feature_id"], config=body.get("config"))
    db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Feature enabled"}}


@router.delete("/tenants/{tenant_id}/features/{feature_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def disable_feature(tenant_id: str, feature_id: str,
                         user: dict | None=None, db: Session = Depends(get_db)):
    result = SaaSCPEngine(db).disable_tenant_feature(tenant_id, feature_id)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/tenants/{tenant_id}/features",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_tenant_features(tenant_id: str,
                              user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).list_tenant_features(tenant_id)
    return {"status": "success", "data": data}


# ----------------------------------------------------------- usage tracking
@router.post("/usage",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_usage(body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    required = ["tenant_id", "usage_type", "usage_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    uid = SaaSCPEngine(db).record_usage(
        body["tenant_id"], body["usage_type"], body["usage_value"],
        period_start=body.get("period_start"), period_end=body.get("period_end"))
    db.commit()
    return {"status": "success", "data": {"id": uid, "message": "Usage recorded"}}


@router.get("/usage",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_usage(usage_type: str | None = None, limit: int = 50,
                    user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).list_usage(user["tenant_id"], usage_type=usage_type, limit=limit)
    return {"status": "success", "data": data}


@router.get("/usage/summary",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def usage_summary(usage_type: str = "api_calls",
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = SaaSCPEngine(db).get_usage_summary(user["tenant_id"], usage_type)
    return {"status": "success", "data": data}
