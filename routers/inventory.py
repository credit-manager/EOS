"""
P25 Inventory Management Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.inventory_engine import InventoryEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Inventory"])


@router.get("/companies/{cid}/warehouses", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_warehouses(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": InventoryEngine(db).list_warehouses(cid, tenant_id=user["tenant_id"])}


@router.post("/companies/{cid}/warehouses", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_warehouse(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "name required"}})
    wid = InventoryEngine(db).create_warehouse(user["tenant_id"], cid, body["name"],
                                                code=body.get("code"), location=body.get("location"))
    db.commit()
    return {"status": "success", "data": {"id": wid}}


@router.get("/companies/{cid}/stock", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_stock(cid: str, item_id: str | None = None, warehouse_id: str | None = None,
                    user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": InventoryEngine(db).get_stock(cid, item_id=item_id,
                                                                         warehouse_id=warehouse_id,
                                                                         tenant_id=user["tenant_id"])}


@router.post("/companies/{cid}/stock/receive", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def receive_stock(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("item_id", "warehouse_id", "quantity"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    result = InventoryEngine(db).receive_stock(cid, user["tenant_id"], body["item_id"],
                                                body["warehouse_id"], body["quantity"],
                                                movement_type=body.get("movement_type", "purchase_receive"),
                                                reference_type=body.get("reference_type"),
                                                reference_id=body.get("reference_id"),
                                                notes=body.get("notes"), moved_by=user.get("id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "STOCK_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/companies/{cid}/stock/issue", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def issue_stock(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("item_id", "warehouse_id", "quantity"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    result = InventoryEngine(db).issue_stock(cid, user["tenant_id"], body["item_id"],
                                              body["warehouse_id"], body["quantity"],
                                              movement_type=body.get("movement_type", "sales_issue"),
                                              reference_type=body.get("reference_type"),
                                              reference_id=body.get("reference_id"),
                                              notes=body.get("notes"), moved_by=user.get("id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "STOCK_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/companies/{cid}/stock/transfer", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def transfer_stock(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("item_id", "from_warehouse_id", "to_warehouse_id", "quantity"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    result = InventoryEngine(db).transfer_stock(cid, user["tenant_id"], body["item_id"],
                                                 body["from_warehouse_id"], body["to_warehouse_id"],
                                                 body["quantity"], notes=body.get("notes"),
                                                 moved_by=user.get("id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "TRANSFER_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/stock/movements", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_movements(cid: str, item_id: str | None = None, warehouse_id: str | None = None,
                         movement_type: str | None = None,
                         user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": InventoryEngine(db).list_movements(cid, item_id=item_id,
                                                                               warehouse_id=warehouse_id,
                                                                               movement_type=movement_type,
                                                                               tenant_id=user["tenant_id"])}


@router.get("/companies/{cid}/stock/alerts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def low_stock_alerts(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": InventoryEngine(db).get_low_stock_alerts(cid, tenant_id=user["tenant_id"])}
