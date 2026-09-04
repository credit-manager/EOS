"""P26 Sales & Invoicing Router — authenticated and tenant-scoped."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.auth import require_permission
from core.auth_adapter import get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.sales_engine import SalesEngine
from database import get_db
router=APIRouter(prefix="/api/v1/dynamic",tags=["Sales & Invoicing"])

def _bad(exc):
    if isinstance(exc,ValueError):raise HTTPException(404,detail={"status":"error","error":{"code":"NOT_FOUND","message":str(exc)}}) from exc
    raise exc

def _company(db,cid,tid):
    if not db.execute(text("SELECT id FROM dbp_companies WHERE id=:cid AND tenant_id=:tid"),{"cid":cid,"tid":tid}).fetchone():raise HTTPException(404,detail={"status":"error","error":{"code":"COMPANY_NOT_FOUND","message":"Company not found in current tenant"}})

@router.get("/companies/{cid}/customers",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def list_customers(cid,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):_company(db,cid,user["tenant_id"]);return {"status":"success","data":SalesEngine(db).list_customers(cid,user["tenant_id"])}
@router.post("/companies/{cid}/customers",dependencies=[Depends(require_permission("dynamic","create")),Depends(write_limiter.check)])
async def create_customer(cid,body:dict,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    _company(db,cid,user["tenant_id"])
    if not body.get("name"):raise HTTPException(400,"name required")
    try: cid_=SalesEngine(db).create_customer(user["tenant_id"],cid,body["name"],contact_name=body.get("contact_name"),email=body.get("email"),phone=body.get("phone"),address=body.get("address"),payment_terms=body.get("payment_terms"),credit_limit=body.get("credit_limit",0))
    except ValueError as exc:_bad(exc)
    db.commit();return {"status":"success","data":{"id":cid_}}
@router.get("/companies/{cid}/quotations",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def list_quotations(cid,status=None,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    _company(db,cid,user["tenant_id"]);p={"cid":cid,"tid":user["tenant_id"]};w=["company_id=:cid","tenant_id=:tid"]
    if status:w.append("status=:st");p["st"]=status
    rows=db.execute(text(f"SELECT id,quote_number,customer_id,quote_date,status,total_amount FROM dbp_sales_quotations WHERE {' AND '.join(w)} ORDER BY quote_date DESC"),p).fetchall();return {"status":"success","data":[{"id":r[0],"quote_number":r[1],"customer_id":r[2],"quote_date":str(r[3]) if r[3] else None,"status":r[4],"total_amount":float(r[5] or 0)} for r in rows]}
@router.post("/companies/{cid}/quotations",dependencies=[Depends(require_permission("dynamic","create")),Depends(write_limiter.check)])
async def create_quotation(cid,body:dict,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    _company(db,cid,user["tenant_id"])
    for f in ("customer_id","quote_date","lines"):
        if f not in body:raise HTTPException(400,f"{f} required")
    try:qid=SalesEngine(db).create_quotation(user["tenant_id"],cid,body["customer_id"],body["quote_date"],body["lines"],created_by=user.get("id"),valid_until=body.get("valid_until"),notes=body.get("notes"))
    except ValueError as exc:_bad(exc)
    db.commit();return {"status":"success","data":{"id":qid}}
@router.post("/quotations/{qid}/convert",dependencies=[Depends(require_permission("dynamic","update")),Depends(write_limiter.check)])
async def convert_quotation(qid,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    q=db.execute(text("SELECT company_id FROM dbp_sales_quotations WHERE id=:qid AND tenant_id=:tid"),{"qid":qid,"tid":user["tenant_id"]}).fetchone()
    if not q:raise HTTPException(404,"Quotation not found")
    try:r=SalesEngine(db).convert_quotation_to_order(qid,user["tenant_id"],q[0],user.get("id"))
    except ValueError as exc:_bad(exc)
    if not r["success"]:raise HTTPException(400,r["error"])
    db.commit();return {"status":"success","data":r}
@router.get("/companies/{cid}/sales-orders",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def list_sales_orders(cid,status=None,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):_company(db,cid,user["tenant_id"]);return {"status":"success","data":SalesEngine(db).list_sales_orders(cid,status,user["tenant_id"])}
@router.post("/companies/{cid}/sales-orders",dependencies=[Depends(require_permission("dynamic","create")),Depends(write_limiter.check)])
async def create_sales_order(cid,body:dict,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    _company(db,cid,user["tenant_id"])
    for f in ("customer_id","order_date","lines"):
        if f not in body:raise HTTPException(400,f"{f} required")
    try:oid=SalesEngine(db).create_sales_order(user["tenant_id"],cid,body["customer_id"],body["order_date"],body["lines"],currency_code=body.get("currency_code"),notes=body.get("notes"),created_by=user.get("id"))
    except ValueError as exc:_bad(exc)
    db.commit();return {"status":"success","data":{"id":oid}}
@router.get("/sales-orders/{oid}",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def get_sales_order(oid,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    r=SalesEngine(db).get_sales_order(oid,user["tenant_id"])
    if not r:raise HTTPException(404,"Order not found")
    return {"status":"success","data":r}
@router.get("/companies/{cid}/invoices",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def list_invoices(cid,status=None,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):_company(db,cid,user["tenant_id"]);return {"status":"success","data":SalesEngine(db).list_invoices(cid,status,user["tenant_id"])}
@router.post("/companies/{cid}/invoices",dependencies=[Depends(require_permission("dynamic","create")),Depends(write_limiter.check)])
async def create_invoice(cid,body:dict,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    _company(db,cid,user["tenant_id"])
    for f in ("customer_id","invoice_date","lines"):
        if f not in body:raise HTTPException(400,f"{f} required")
    try:iid=SalesEngine(db).create_invoice(user["tenant_id"],cid,body["customer_id"],body["invoice_date"],body["lines"],order_id=body.get("order_id"),due_date=body.get("due_date"),currency_code=body.get("currency_code"),notes=body.get("notes"),created_by=user.get("id"))
    except ValueError as exc:_bad(exc)
    db.commit();return {"status":"success","data":{"id":iid}}
@router.get("/invoices/{iid}",dependencies=[Depends(require_permission("dynamic","read")),Depends(read_limiter.check)])
async def get_invoice(iid,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    r=SalesEngine(db).get_invoice(iid,user["tenant_id"])
    if not r:raise HTTPException(404,"Invoice not found")
    return {"status":"success","data":r}
@router.post("/invoices/{iid}/payments",dependencies=[Depends(require_permission("dynamic","update")),Depends(write_limiter.check)])
async def record_payment(iid,body:dict,user:dict=Depends(get_current_user),db:Session=Depends(get_db)):
    if "amount" not in body or body["amount"]<=0:raise HTTPException(400,"Positive amount required")
    r=SalesEngine(db).record_payment(iid,body["amount"],body.get("payment_date",""),user["tenant_id"])
    if not r["success"]:raise HTTPException(400,r["error"])
    db.commit();return {"status":"success","data":r}
