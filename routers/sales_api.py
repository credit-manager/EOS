"""
EOS Sales CRM Router — /api/v1/sales
Direct customer/lead/opportunity CRUD for the React frontend.
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import get_current_user

router = APIRouter(prefix="/api/v1/sales", tags=["Sales CRM"])


def _tenant(user: dict) -> str:
    tenant_id = str(user.get("tenant_id") or "").strip().lower()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authenticated tenant is required")
    return tenant_id


# ─── Customers ─────────────────────────────────────

@router.get("/customers")
async def list_customers(
    type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant(user)
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id}
    if type:
        conditions.append("type = :type")
        params["type"] = type
    if search:
        conditions.append("(name ILIKE :search OR email ILIKE :search OR name_ar ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    total = db.execute(text(f"SELECT COUNT(*) FROM customers WHERE {where}"), params).scalar() or 0
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(
        "SELECT id, name, name_ar, type, email, phone, address, tax_id, total_orders, total_spent, created_at, is_active "
        f"FROM customers WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    ), params).fetchall()
    data = [{
        "id": r[0], "name": r[1], "name_ar": r[2], "type": r[3] or "individual",
        "email": r[4], "phone": r[5], "address": r[6], "tax_id": r[7],
        "total_orders": r[8] or 0, "total_spent": float(r[9]) if r[9] else 0,
        "created_at": r[10].isoformat() if r[10] else None,
        "is_active": r[11] if r[11] is not None else True,
    } for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    r = db.execute(text(
        "SELECT id, name, name_ar, type, email, phone, address, tax_id, total_orders, total_spent, created_at, is_active "
        "FROM customers WHERE id = :id AND tenant_id = :tenant_id"
    ), {"id": customer_id, "tenant_id": tenant_id}).fetchone()
    if not r:
        raise HTTPException(404, detail="Customer not found")
    return {
        "id": r[0], "name": r[1], "name_ar": r[2], "type": r[3] or "individual",
        "email": r[4], "phone": r[5], "address": r[6], "tax_id": r[7],
        "total_orders": r[8] or 0, "total_spent": float(r[9]) if r[9] else 0,
        "created_at": r[10].isoformat() if r[10] else None,
        "is_active": r[11] if r[11] is not None else True,
    }


@router.post("/customers", status_code=201)
async def create_customer(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail="name required")
    tenant_id = _tenant(user)
    cid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(text(
        "INSERT INTO customers (id, tenant_id, name, name_ar, type, email, phone, address, tax_id, total_orders, total_spent, created_at, updated_at, is_active) "
        "VALUES (:id, :tenant_id, :name, :name_ar, :type, :email, :phone, :address, :tax_id, 0, 0, :now, :now, true)"
    ), {
        "id": cid, "tenant_id": tenant_id, "name": body["name"], "name_ar": body.get("name_ar"),
        "type": body.get("type", "individual"), "email": body.get("email"), "phone": body.get("phone"),
        "address": body.get("address"), "tax_id": body.get("tax_id"), "now": now,
    })
    db.commit()
    return {"id": cid, "name": body["name"], "message": "Customer created"}


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    existing = db.execute(text("SELECT id FROM customers WHERE id = :id AND tenant_id = :tenant_id"),
                          {"id": customer_id, "tenant_id": tenant_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Customer not found")
    fields = []
    params: dict = {"id": customer_id, "tenant_id": tenant_id, "now": datetime.now(timezone.utc)}
    for col in ("name", "name_ar", "type", "email", "phone", "address", "tax_id"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        fields.append("updated_at = :now")
        db.execute(text(f"UPDATE customers SET {', '.join(fields)} WHERE id = :id AND tenant_id = :tenant_id"), params)
        db.commit()
    return {"message": "Customer updated"}


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    result = db.execute(text("DELETE FROM customers WHERE id = :id AND tenant_id = :tenant_id"),
                        {"id": customer_id, "tenant_id": tenant_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Customer not found")
    db.commit()
    return {"message": "Customer deleted"}


# ─── Leads ─────────────────────────────────────

@router.get("/leads")
async def list_leads(status: Optional[str] = None, search: Optional[str] = None,
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id}
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if search:
        conditions.append("(first_name ILIKE :search OR last_name ILIKE :search OR company_name ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    try:
        total = db.execute(text(f"SELECT COUNT(*) FROM leads WHERE {where}"), params).scalar() or 0
        params.update(limit=page_size, offset=(page - 1) * page_size)
        rows = db.execute(text(
            "SELECT id, first_name, last_name, company_name, email, phone, source, status, score, notes, created_at "
            f"FROM leads WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ), params).fetchall()
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Sales CRM lead storage is unavailable")
    data = [{
        "id": r[0], "first_name": r[1], "last_name": r[2], "company_name": r[3], "email": r[4],
        "phone": r[5], "source": r[6], "status": r[7] or "new", "score": r[8] or 0,
        "notes": r[9], "created_at": r[10].isoformat() if r[10] else None,
    } for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/leads", status_code=201)
async def create_lead(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    lid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(text(
            "INSERT INTO leads (id, tenant_id, first_name, last_name, company_name, email, phone, source, status, score, notes, created_at) "
            "VALUES (:id, :tenant_id, :fn, :ln, :cn, :email, :phone, :src, 'new', 0, :notes, :now)"
        ), {"id": lid, "tenant_id": tenant_id, "fn": body.get("first_name", ""), "ln": body.get("last_name", ""),
            "cn": body.get("company_name"), "email": body.get("email"), "phone": body.get("phone"),
            "src": body.get("source"), "notes": body.get("notes"), "now": now})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create lead")
    return {"id": lid, "message": "Lead created"}


# ─── Opportunities ─────────────────────────────────

@router.get("/opportunities")
async def list_opportunities(stage: Optional[str] = None, customer_id: Optional[str] = None,
                             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id}
    if stage:
        conditions.append("stage = :stage")
        params["stage"] = stage
    if customer_id:
        conditions.append("customer_id = :cid")
        params["cid"] = customer_id
    where = " AND ".join(conditions)
    try:
        total = db.execute(text(f"SELECT COUNT(*) FROM opportunities WHERE {where}"), params).scalar() or 0
        params.update(limit=page_size, offset=(page - 1) * page_size)
        rows = db.execute(text(
            "SELECT id, name, customer_id, stage, amount, probability, expected_close_date, notes, created_at "
            f"FROM opportunities WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ), params).fetchall()
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Sales CRM opportunity storage is unavailable")
    data = [{
        "id": r[0], "name": r[1], "customer_id": r[2], "stage": r[3] or "prospecting",
        "amount": float(r[4]) if r[4] else 0, "probability": r[5] or 0,
        "expected_close_date": r[6].isoformat() if r[6] else None,
        "notes": r[7], "created_at": r[8].isoformat() if r[8] else None,
    } for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/opportunities", status_code=201)
async def create_opportunity(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    oid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(text(
            "INSERT INTO opportunities (id, tenant_id, name, customer_id, stage, amount, probability, notes, created_at) "
            "VALUES (:id, :tenant_id, :name, :cid, :stage, :amt, :prob, :notes, :now)"
        ), {"id": oid, "tenant_id": tenant_id, "name": body.get("name", ""), "cid": body.get("customer_id"),
            "stage": body.get("stage", "prospecting"), "amt": body.get("amount", 0),
            "prob": body.get("probability", 0), "notes": body.get("notes"), "now": now})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create opportunity")
    return {"id": oid, "message": "Opportunity created"}


# ─── Compatibility endpoints ─────────────────────

@router.get("/quotes")
async def list_quotes(status: Optional[str] = None, customer_id: Optional[str] = None,
                      page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                      user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"data": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/quotes", status_code=201)
async def create_quote(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"id": str(uuid.uuid4()), "message": "Quote endpoint is not implemented"}


@router.get("/pipeline/summary")
async def pipeline_summary(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"total_value": 0, "deal_count": 0, "avg_deal_size": 0}


@router.get("/pipeline/by-stage")
async def pipeline_by_stage(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return []


@router.get("/pipeline/forecast")
async def pipeline_forecast(period_days: int = Query(30, ge=1), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"forecast": 0, "period_days": period_days}


@router.get("/reports/sales")
async def sales_report(start_date: Optional[str] = None, end_date: Optional[str] = None,
                       user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"total_sales": 0, "invoice_count": 0, "top_products": []}


@router.get("/reports/top-customers")
async def top_customers_report(limit: int = Query(10, ge=1, le=50), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return []


@router.get("/reports/top-products")
async def top_products_report(limit: int = Query(10, ge=1, le=50), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return []
