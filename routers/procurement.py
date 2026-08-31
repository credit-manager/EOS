"""
P24 Procurement & Purchase Orders Router
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.procurement_engine import ProcurementEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Procurement"])


@router.get("/companies/{cid}/items", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_items(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ProcurementEngine(db).list_items(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/items", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_item(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("code", "name_en", "item_type"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    iid = ProcurementEngine(db).create_item(user.get("tenant_id"), cid, body["code"], body["name_en"],
                                             body["item_type"], **{k: v for k, v in body.items() if k not in ("code", "name_en", "item_type")})
    db.commit()
    return {"status": "success", "data": {"id": iid}}


@router.get("/companies/{cid}/suppliers", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_suppliers(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ProcurementEngine(db).list_suppliers(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/suppliers", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_supplier(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "name required"}})
    sid = ProcurementEngine(db).create_supplier(user.get("tenant_id"), cid, body["name"], **{k: v for k, v in body.items() if k != "name"})
    db.commit()
    return {"status": "success", "data": {"id": sid}}


@router.get("/companies/{cid}/purchase-requests", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_purchase_requests(cid: str, status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ProcurementEngine(db).list_purchase_requests(cid, status=status, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/purchase-requests", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_purchase_request(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rid = ProcurementEngine(db).create_purchase_request(user.get("tenant_id"), cid, user.get("id") or "unknown", **body)
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.post("/purchase-requests/{rid}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve_purchase_request(rid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProcurementEngine(db).approve_purchase_request(rid, user.get("id") or "admin", user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/purchase-orders", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_purchase_orders(cid: str, status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ProcurementEngine(db).list_purchase_orders(cid, status=status, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/purchase-orders", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_purchase_order(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("supplier_id", "order_date", "lines"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    oid = ProcurementEngine(db).create_purchase_order(user.get("tenant_id"), cid, body["supplier_id"],
                                                       body["order_date"], body["lines"],
                                                       created_by=user.get("id") or "system",
                                                       **{k: v for k, v in body.items() if k not in ("supplier_id", "order_date", "lines", "created_by")})
    db.commit()
    return {"status": "success", "data": {"id": oid}}


@router.get("/purchase-orders/{oid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_purchase_order(oid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    po = ProcurementEngine(db).get_purchase_order(oid, user.get("tenant_id"))
    if not po:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Order not found"}})
    return {"status": "success", "data": po}


@router.post("/purchase-orders/{oid}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve_purchase_order(oid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProcurementEngine(db).approve_purchase_order(oid, user.get("id") or "admin", user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/purchase-orders/{oid}/receive", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def receive_goods(oid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("line_id", "quantity", "received_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    result = ProcurementEngine(db).receive_goods(oid, body["line_id"], body["quantity"],
                                                  body["received_date"], user.get("id") or "admin",
                                                  tenant_id=user.get("tenant_id"),
                                                  notes=body.get("notes"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "RECEIVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}
