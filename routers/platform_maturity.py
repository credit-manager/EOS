from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.platform_maturity import PlatformMaturityEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/platform", tags=["Platform Maturity"])


@router.get("/certifications", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_certifications(status: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": PlatformMaturityEngine(db).list_scores(user["tenant_id"], status=status)}


@router.post("/certifications", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_certification(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["certification_level", "total_score", "max_score"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    sid = PlatformMaturityEngine(db).create_score(user["tenant_id"], body["certification_level"],
        body["total_score"], body["max_score"], status=body.get("status", "pending"),
        expires_at=body.get("expires_at"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Certification created"}}


@router.get("/certifications/{score_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_certification(score_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    data = PlatformMaturityEngine(db).get_score(user["tenant_id"], score_id)
    if not data:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found"}})
    return {"status": "success", "data": data}


@router.get("/metrics", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_metrics(metric_category: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": PlatformMaturityEngine(db).list_metrics(user["tenant_id"], metric_category=metric_category)}


@router.post("/metrics", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_metric(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["metric_category", "metric_name", "metric_value"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    mid = PlatformMaturityEngine(db).record_metric(user["tenant_id"], body["metric_category"],
        body["metric_name"], body["metric_value"], target_value=body.get("target_value"))
    db.commit()
    return {"status": "success", "data": {"id": mid, "message": "Metric recorded"}}


@router.get("/features", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_features(feature_category: str | None = None, is_stable: bool | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": PlatformMaturityEngine(db).list_features(
        feature_category=feature_category, is_stable=is_stable)}


@router.post("/features", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def register_feature(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["feature_name", "feature_category", "version_added"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = PlatformMaturityEngine(db).register_feature(body["feature_name"], body["feature_category"],
        body["version_added"], is_stable=body.get("is_stable", False), metadata=body.get("metadata"))
    db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Feature registered"}}


@router.put("/features/{feature_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_feature(feature_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = PlatformMaturityEngine(db).update_feature(feature_id, **body)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/upgrades", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_upgrades(upgrade_type: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": PlatformMaturityEngine(db).list_upgrades(user["tenant_id"], upgrade_type=upgrade_type)}


@router.post("/upgrades", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_upgrade(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["from_version", "to_version", "upgrade_type"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    uid = PlatformMaturityEngine(db).record_upgrade(user["tenant_id"], body["from_version"],
        body["to_version"], body["upgrade_type"], notes=body.get("notes"))
    db.commit()
    return {"status": "success", "data": {"id": uid, "message": "Upgrade recorded"}}


@router.get("/health", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_health(component_name: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": PlatformMaturityEngine(db).list_health(user["tenant_id"], component_name=component_name)}


@router.post("/health", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_health(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ["component_name", "health_score", "status"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    hid = PlatformMaturityEngine(db).record_health(user["tenant_id"], body["component_name"],
        body["health_score"], body["status"], details=body.get("details"))
    db.commit()
    return {"status": "success", "data": {"id": hid, "message": "Health recorded"}}
