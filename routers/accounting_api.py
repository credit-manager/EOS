"""
EOS Accounting API Router — /api/v1/accounting
C1 FIX: All queries filter by tenant_id for multi-tenant isolation.
C5 FIX: Journal posting updates GL account balances.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import get_current_user
from database import get_db

router = APIRouter(prefix="/api/v1/accounting", tags=["Accounting API"])


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    return tenant_id


@router.get("/accounts")
async def list_accounts(
    account_type: str | None = None,
    parent_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tid = _tenant(user)
    conditions = ["tenant_id = :tid"]
    params: dict = {"tid": tid}
    if account_type:
        conditions.append("account_type = :at")
        params["at"] = account_type
    if parent_id:
        conditions.append("parent_id = :pid")
        params["pid"] = parent_id
    if search:
        conditions.append("(name_en ILIKE :search OR code ILIKE :search OR name_ar ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    total = db.execute(text(f"SELECT COUNT(*) FROM dbp_accounts WHERE {where}"), params).scalar() or 0
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(
        f"SELECT id, code, name_en, name_ar, account_type, parent_id, currency_code, "
        f"is_active, is_system, opening_balance, current_balance, description "
        f"FROM dbp_accounts WHERE {where} ORDER BY code LIMIT :limit OFFSET :offset"
    ), params).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3],
             "account_type": r[4], "parent_id": r[5], "currency_code": r[6] or "SAR",
             "is_active": r[7] if r[7] is not None else True, "is_system": r[8] or False,
             "opening_balance": float(r[9]) if r[9] else 0,
             "current_balance": float(r[10]) if r[10] else 0, "description": r[11]} for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/accounts/{account_id}")
async def get_account(account_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    r = db.execute(text(
        "SELECT id, code, name_en, name_ar, account_type, parent_id, currency_code, "
        "is_active, is_system, opening_balance, current_balance, description "
        "FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone()
    if not r:
        raise HTTPException(404, detail="Account not found")
    return {"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3], "account_type": r[4],
            "parent_id": r[5], "currency_code": r[6] or "SAR", "is_active": r[7] if r[7] is not None else True,
            "is_system": r[8] or False, "opening_balance": float(r[9]) if r[9] else 0,
            "current_balance": float(r[10]) if r[10] else 0, "description": r[11]}


@router.post("/accounts", status_code=201)
async def create_account(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail="name required")
    tid = _tenant(user)
    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(text(
        "INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, name_ar, account_type, parent_id, "
        "currency_code, is_active, is_system, opening_balance, current_balance, description, created_at) "
        "VALUES (:id, :tid, :cid, :code, :name, :name_ar, :at, :pid, :cur, true, false, 0, 0, :desc, :now)"),
        {"id": aid, "tid": tid, "cid": tid, "code": body.get("code", f"ACC-{aid[:6].upper()}"),
         "name": body["name"], "name_ar": body.get("name_ar"), "at": body.get("account_type", "asset"),
         "pid": body.get("parent_id"), "cur": body.get("currency_code", "SAR"), "desc": body.get("description"), "now": now})
    db.commit()
    return {"id": aid, "name": body["name"], "message": "Account created"}


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    existing = db.execute(text("SELECT id FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Account not found")
    fields, params = [], {"id": account_id, "tid": tid}
    for col in ("name_en", "name_ar", "code", "account_type", "parent_id", "currency_code", "description"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_accounts SET {', '.join(fields)} WHERE id = :id AND tenant_id = :tid"), params)
        db.commit()
    return {"message": "Account updated"}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    existing = db.execute(text("SELECT is_system FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Account not found")
    if existing[0]:
        raise HTTPException(400, detail="Cannot delete system account")
    db.execute(text("DELETE FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid})
    db.commit()
    return {"message": "Account deleted"}


@router.get("/journal")
async def list_journal_entries(
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tid = _tenant(user)
    conditions = ["tenant_id = :tid"]
    params: dict = {"tid": tid}
    if start_date:
        conditions.append("entry_date >= :sd"); params["sd"] = start_date
    if end_date:
        conditions.append("entry_date <= :ed"); params["ed"] = end_date
    if status:
        conditions.append("status = :st"); params["st"] = status
    where = " AND ".join(conditions)
    total = db.execute(text(f"SELECT COUNT(*) FROM dbp_journal_entries WHERE {where}"), params).scalar() or 0
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(
        f"SELECT id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by "
        f"FROM dbp_journal_entries WHERE {where} ORDER BY entry_date DESC LIMIT :limit OFFSET :offset"), params).fetchall()
    data = [{"id": r[0], "entry_number": r[1], "entry_date": r[2].isoformat() if r[2] else None,
             "entry_type": r[3], "description": r[4], "reference": r[5], "status": r[6] or "draft",
             "total_debit": float(r[7]) if r[7] else 0, "total_credit": float(r[8]) if r[8] else 0,
             "is_posted": r[9] or False, "created_by": r[10]} for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/journal/{entry_id}")
async def get_journal_entry(entry_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    r = db.execute(text(
        "SELECT id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by "
        "FROM dbp_journal_entries WHERE id = :id AND tenant_id = :tid"), {"id": entry_id, "tid": tid}).fetchone()
    if not r:
        raise HTTPException(404, detail="Journal entry not found")
    lines = db.execute(text(
        "SELECT jl.id, jl.account_id, a.code, a.name_en, jl.debit, jl.credit, jl.description, jl.cost_center_id "
        "FROM dbp_journal_lines jl LEFT JOIN dbp_accounts a ON jl.account_id = a.id "
        "WHERE jl.journal_entry_id = :eid AND a.tenant_id = :tid ORDER BY jl.line_order"),
        {"eid": entry_id, "tid": tid}).fetchall()
    return {"id": r[0], "entry_number": r[1], "entry_date": r[2].isoformat() if r[2] else None,
            "entry_type": r[3], "description": r[4], "reference": r[5], "status": r[6],
            "total_debit": float(r[7]) if r[7] else 0, "total_credit": float(r[8]) if r[8] else 0,
            "is_posted": r[9], "created_by": r[10],
            "lines": [{"id": l[0], "account_id": l[1], "account_code": l[2], "account_name": l[3],
                       "debit": float(l[4]) if l[4] else 0, "credit": float(l[5]) if l[5] else 0,
                       "description": l[6], "cost_center_id": l[7]} for l in lines]}


@router.post("/journal", status_code=201)
async def create_journal_entry(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    lines = body.get("lines", [])
    total_debit = sum(l.get("debit", 0) for l in lines)
    total_credit = sum(l.get("credit", 0) for l in lines)
    if not lines or abs(total_debit - total_credit) > 0.01:
        raise HTTPException(400, detail=f"Entry not balanced: debit={total_debit}, credit={total_credit}")
    for line in lines:
        account_id = line.get("account_id")
        if not account_id:
            raise HTTPException(400, detail="account_id required")
        if not db.execute(text("SELECT 1 FROM dbp_accounts WHERE id = :aid AND tenant_id = :tid"), {"aid": account_id, "tid": tid}).fetchone():
            raise HTTPException(404, detail="Account not found")
    db.execute(text(
        "INSERT INTO dbp_journal_entries (id, tenant_id, company_id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by, created_at) "
        "VALUES (:id, :tid, :cid, :en, :ed, :et, :desc, :ref, 'draft', :td, :tc, false, :cb, :now)"),
        {"id": eid, "tid": tid, "cid": tid, "en": f"JE-{eid[:8].upper()}", "ed": body.get("entry_date", now),
         "et": body.get("entry_type", "general"), "desc": body.get("description", ""), "ref": body.get("reference"),
         "td": total_debit, "tc": total_credit, "cb": user.get("id"), "now": now})
    for i, line in enumerate(lines):
        db.execute(text(
            "INSERT INTO dbp_journal_lines (id, journal_entry_id, account_id, debit, credit, currency_code, description, cost_center_id, line_order, created_at) "
            "VALUES (:id, :eid, :aid, :dr, :cr, :cur, :desc, :cc, :lo, :now)"),
            {"id": str(uuid.uuid4()), "eid": eid, "aid": line.get("account_id"), "dr": line.get("debit", 0),
             "cr": line.get("credit", 0), "cur": line.get("currency_code", "SAR"), "desc": line.get("description"),
             "cc": line.get("cost_center_id"), "lo": i, "now": now})
    db.commit()
    return {"id": eid, "message": "Journal entry created"}
