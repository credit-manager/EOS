"""
P26 Sales & Invoicing Router
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.sales_engine import SalesEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Sales & Invoicing"])


@router.get("/companies/{cid}/customers", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_customers(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": SalesEngine(db).list_customers(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/customers", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_customer(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "name required"}})
    cust_id = SalesEngine(db).create_customer(user.get("tenant_id"), cid, body["name"],
                                               contact_name=body.get("contact_name"),
                                               email=body.get("email"), phone=body.get("phone"),
                                               address=body.get("address"),
                                               payment_terms=body.get("payment_terms"),
                                               credit_limit=body.get("credit_limit", 0))
    db.commit()
    return {"status": "success", "data": {"id": cust_id}}


@router.get("/companies/{cid}/quotations", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_quotations(cid: str, status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    conditions = ["company_id = :cid", "tenant_id = :tid"]
    params = {"cid": cid, "tid": user.get("tenant_id")}
    if status:
        conditions.append("status = :st")
        params["st"] = status
    from sqlalchemy import text
    rows = db.execute(text(
        f"SELECT id, quote_number, customer_id, quote_date, status, total_amount "
        f"FROM dbp_sales_quotations WHERE {' AND '.join(conditions)} ORDER BY quote_date DESC"
    ), params).fetchall()
    return {"status": "success", "data": [{"id": r[0], "quote_number": r[1], "customer_id": r[2],
                                           "quote_date": str(r[3]) if r[3] else None,
                                           "status": r[4], "total_amount": float(r[5]) if r[5] else 0}
                                          for r in rows]}


@router.post("/companies/{cid}/quotations", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_quotation(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("customer_id", "quote_date", "lines"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    qid = SalesEngine(db).create_quotation(user.get("tenant_id"), cid, body["customer_id"],
                                            body["quote_date"], body["lines"],
                                            created_by=user.get("id") or "system",
                                            valid_until=body.get("valid_until"),
                                            notes=body.get("notes"))
    db.commit()
    return {"status": "success", "data": {"id": qid}}


@router.post("/quotations/{qid}/convert", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def convert_quotation(qid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import text as sa
    q = db.execute(sa("SELECT company_id FROM dbp_sales_quotations WHERE id = :qid AND tenant_id = :tid"),
                   {"qid": qid, "tid": user.get("tenant_id")}).fetchone()
    if not q:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Quotation not found"}})
    result = SalesEngine(db).convert_quotation_to_order(qid, user.get("tenant_id"), q[0],
                                                         created_by=user.get("id") or "admin")
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "CONVERT_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/sales-orders", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_sales_orders(cid: str, status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": SalesEngine(db).list_sales_orders(cid, status=status, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/sales-orders", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_sales_order(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("customer_id", "order_date", "lines"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    oid = SalesEngine(db).create_sales_order(user.get("tenant_id"), cid, body["customer_id"],
                                              body["order_date"], body["lines"],
                                              currency_code=body.get("currency_code"),
                                              notes=body.get("notes"),
                                              created_by=user.get("id") or "system")
    db.commit()
    return {"status": "success", "data": {"id": oid}}


@router.get("/sales-orders/{oid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_sales_order(oid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    order = SalesEngine(db).get_sales_order(oid, user.get("tenant_id"))
    if not order:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Order not found"}})
    return {"status": "success", "data": order}


@router.get("/companies/{cid}/invoices", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_invoices(cid: str, status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": SalesEngine(db).list_invoices(cid, status=status, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/invoices", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_invoice(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("customer_id", "invoice_date", "lines"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    iid = SalesEngine(db).create_invoice(user.get("tenant_id"), cid, body["customer_id"],
                                          body["invoice_date"], body["lines"],
                                          order_id=body.get("order_id"),
                                          due_date=body.get("due_date"),
                                          currency_code=body.get("currency_code"),
                                          notes=body.get("notes"),
                                          created_by=user.get("id") or "system")
    db.commit()
    return {"status": "success", "data": {"id": iid}}


@router.get("/invoices/{iid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_invoice(iid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = SalesEngine(db).get_invoice(iid, user.get("tenant_id"))
    if not inv:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Invoice not found"}})
    return {"status": "success", "data": inv}


@router.post("/invoices/{iid}/payments", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def record_payment(iid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "amount" not in body or body["amount"] <= 0:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Positive amount required"}})
    result = SalesEngine(db).record_payment(iid, body["amount"], body.get("payment_date", ""),
                                            user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "PAYMENT_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}
