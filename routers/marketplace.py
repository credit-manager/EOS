"""
P55 Marketplace Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.marketplace_engine import MarketplaceEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/marketplace", tags=["Marketplace"])


@router.get("/items", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_items(item_type: str | None = None,
                     is_featured: bool | None = None,
                     is_free: bool | None = None,
                     db: Session=None):
    return {"status": "success", "data": MarketplaceEngine(db).list_items(
        item_type=item_type, is_featured=is_featured, is_free=is_free)}


@router.get("/items/{item_code}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_item(item_code: str, db: Session=None):
    item = MarketplaceEngine(db).get_item(item_code)
    if not item:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Item not found"}})
    return {"status": "success", "data": item}


@router.post("/install", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def install(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    item_code = body.get("item_code")
    if not item_code:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "item_code required"}})
    result = MarketplaceEngine(db).install_item(user.get("tenant_id"), item_code, user.get("id") or "system")
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INSTALL_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/installations/{inst_id}/apply", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def apply(inst_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = MarketplaceEngine(db).apply_installation(
        user.get("tenant_id"), inst_id, body.get("project_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPLY_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/user/installations", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_installations(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": MarketplaceEngine(db).list_user_installations(user.get("tenant_id"))}


@router.delete("/user/installations/{item_code}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def uninstall(item_code: str, user: dict | None=None, db: Session = Depends(get_db)):
    result = MarketplaceEngine(db).uninstall_item(user.get("tenant_id"), item_code, user.get("id") or "admin")
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UNINSTALL_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}