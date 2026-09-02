"""
P29 Fixed Assets Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.fixed_asset_engine import FixedAssetEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Fixed Assets"])


@router.get("/companies/{cid}/fixed-assets", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_assets(cid: str, status: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FixedAssetEngine(db).list_assets(cid, tenant_id=user.get("tenant_id"), status=status)}


@router.post("/companies/{cid}/fixed-assets", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_asset(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("name", "acquisition_date", "acquisition_cost", "useful_life_years"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    aid = FixedAssetEngine(db).create_asset(user.get("tenant_id"), cid, body["name"],
                                             body["acquisition_date"], body["acquisition_cost"],
                                             body["useful_life_years"],
                                             description=body.get("description"),
                                             category=body.get("category"),
                                             salvage_value=body.get("salvage_value", 0),
                                             depreciation_method=body.get("depreciation_method", "straight_line"),
                                             location=body.get("location"),
                                             employee_id=body.get("employee_id"))
    db.commit()
    return {"status": "success", "data": {"id": aid}}


@router.get("/fixed-assets/{aid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_asset(aid: str, db: Session=None):
    asset = FixedAssetEngine(db).get_asset(aid)
    if not asset:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Asset not found"}})
    return {"status": "success", "data": asset}


@router.put("/fixed-assets/{aid}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_asset(aid: str, body: dict, db: Session=None):
    result = FixedAssetEngine(db).update_asset(aid, **body)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UPDATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/fixed-assets/{aid}/dispose", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def dispose_asset(aid: str, body: dict, db: Session=None):
    if "disposal_date" not in body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "disposal_date required"}})
    result = FixedAssetEngine(db).dispose_asset(aid, body["disposal_date"],
                                                 disposal_amount=body.get("disposal_amount"),
                                                 notes=body.get("notes"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "DISPOSE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/companies/{cid}/depreciation/run", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def run_depreciation(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("period_start", "period_end"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = FixedAssetEngine(db).run_depreciation(user.get("tenant_id"), cid,
                                                 body["period_start"], body["period_end"],
                                                 processed_by=user.get("id"))
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.get("/companies/{cid}/depreciation/runs", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_depreciation_runs(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FixedAssetEngine(db).list_depreciation_runs(cid, tenant_id=user.get("tenant_id"))}


@router.get("/depreciation/runs/{rid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_depreciation_run(rid: str, db: Session=None):
    run = FixedAssetEngine(db).get_depreciation_run(rid)
    if not run:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Run not found"}})
    return {"status": "success", "data": run}


@router.post("/fixed-assets/{aid}/transfer", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def transfer_asset(aid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("to_location", "transfer_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        tid = FixedAssetEngine(db).transfer_asset(aid, body["to_location"], body["transfer_date"],
                                                   user.get("id") or "admin", notes=body.get("notes"))
    except ValueError as e:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "TRANSFER_FAILED", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": tid}}


@router.get("/fixed-assets/{aid}/transfers", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_transfers(aid: str, db: Session=None):
    return {"status": "success", "data": FixedAssetEngine(db).list_asset_transfers(asset_id=aid)}
