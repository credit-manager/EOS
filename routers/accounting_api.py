"""
EOS Accounting API Router — /api/v1/accounting
All endpoints require an authenticated tenant and scope database access by tenant_id.
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
async def list_accounts(account_type: str | None = None, parent_id: str | None = None,
                        search: str | None = None, page: int = Query(1, ge=1),
                        page_size: int = Query(50, ge=1, le=200),
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    conditions = ["tenant_id = :tid"]
    params: dict = {"tid": tid}
    if account_type:
        conditions.append("account_type = :at"); params["at"] = account_type
    if parent_id:
        conditions.append("parent_id = :pid"); params["pid"] = parent_id
    if search:
        conditions.append("(name_en ILIKE :search OR code ILIKE :search OR name_ar ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    total = db.execute(text(f"SELECT COUNT(*) FROM dbp_accounts WHERE {where}"), params).scalar() or 0
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(f"SELECT id, code, name_en, name_ar, account_type, parent_id, currency_code, is_active, is_system, opening_balance, current_balance, description FROM dbp_accounts WHERE {where} ORDER BY code LIMIT :limit OFFSET :offset"), params).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3], "account_type": r[4], "parent_id": r[5], "currency_code": r[6] or "SAR", "is_active": r[7] if r[7] is not None else True, "is_system": r[8] or False, "opening_balance": float(r[9]) if r[9] else 0, "current_balance": float(r[10]) if r[10] else 0, "description": r[11]} for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/accounts/{account_id}")
async def get_account(account_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    r = db.execute(text("SELECT id, code, name_en, name_ar, account_type, parent_id, currency_code, is_active, is_system, opening_balance, current_balance, description FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone()
    if not r:
        raise HTTPException(404, detail="Account not found")
    return {"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3], "account_type": r[4], "parent_id": r[5], "currency_code": r[6] or "SAR", "is_active": r[7] if r[7] is not None else True, "is_system": r[8] or False, "opening_balance": float(r[9]) if r[9] else 0, "current_balance": float(r[10]) if r[10] else 0, "description": r[11]}


@router.post("/accounts", status_code=201)
async def create_account(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail="name required")
    tid = _tenant(user)
    aid = str(uuid.uuid4()); now = datetime.now(timezone.utc)
    db.execute(text("INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, name_ar, account_type, parent_id, currency_code, is_active, is_system, opening_balance, current_balance, description, created_at) VALUES (:id, :tid, :cid, :code, :name, :name_ar, :at, :pid, :cur, true, false, 0, 0, :desc, :now)"), {"id": aid, "tid": tid, "cid": tid, "code": body.get("code", f"ACC-{aid[:6].upper()}"), "name": body["name"], "name_ar": body.get("name_ar"), "at": body.get("account_type", "asset"), "pid": body.get("parent_id"), "cur": body.get("currency_code", "SAR"), "desc": body.get("description"), "now": now})
    db.commit()
    return {"id": aid, "name": body["name"], "message": "Account created"}


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    if not db.execute(text("SELECT 1 FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone():
        raise HTTPException(404, detail="Account not found")
    fields, params = [], {"id": account_id, "tid": tid}
    for col in ("name_en", "name_ar", "code", "account_type", "parent_id", "currency_code", "description"):
        if col in body:
            fields.append(f"{col} = :{col}"); params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_accounts SET {', '.join(fields)} WHERE id = :id AND tenant_id = :tid"), params); db.commit()
    return {"message": "Account updated"}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    existing = db.execute(text("SELECT is_system FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}).fetchone()
    if not existing: raise HTTPException(404, detail="Account not found")
    if existing[0]: raise HTTPException(400, detail="Cannot delete system account")
    db.execute(text("DELETE FROM dbp_accounts WHERE id = :id AND tenant_id = :tid"), {"id": account_id, "tid": tid}); db.commit()
    return {"message": "Account deleted"}


@router.get("/journal")
async def list_journal_entries(start_date: str | None = None, end_date: str | None = None, status: str | None = None,
                               page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                               user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); conditions = ["tenant_id = :tid"]; params: dict = {"tid": tid}
    if start_date: conditions.append("entry_date >= :sd"); params["sd"] = start_date
    if end_date: conditions.append("entry_date <= :ed"); params["ed"] = end_date
    if status: conditions.append("status = :st"); params["st"] = status
    where = " AND ".join(conditions)
    total = db.execute(text(f"SELECT COUNT(*) FROM dbp_journal_entries WHERE {where}"), params).scalar() or 0
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(f"SELECT id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by FROM dbp_journal_entries WHERE {where} ORDER BY entry_date DESC LIMIT :limit OFFSET :offset"), params).fetchall()
    data = [{"id": r[0], "entry_number": r[1], "entry_date": r[2].isoformat() if r[2] else None, "entry_type": r[3], "description": r[4], "reference": r[5], "status": r[6] or "draft", "total_debit": float(r[7]) if r[7] else 0, "total_credit": float(r[8]) if r[8] else 0, "is_posted": r[9] or False, "created_by": r[10]} for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/journal/{entry_id}")
async def get_journal_entry(entry_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    r = db.execute(text("SELECT id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by FROM dbp_journal_entries WHERE id = :id AND tenant_id = :tid"), {"id": entry_id, "tid": tid}).fetchone()
    if not r: raise HTTPException(404, detail="Journal entry not found")
    lines = db.execute(text("SELECT jl.id, jl.account_id, a.code, a.name_en, jl.debit, jl.credit, jl.description, jl.cost_center_id FROM dbp_journal_lines jl LEFT JOIN dbp_accounts a ON jl.account_id = a.id WHERE jl.journal_entry_id = :eid AND a.tenant_id = :tid ORDER BY jl.line_order"), {"eid": entry_id, "tid": tid}).fetchall()
    return {"id": r[0], "entry_number": r[1], "entry_date": r[2].isoformat() if r[2] else None, "entry_type": r[3], "description": r[4], "reference": r[5], "status": r[6], "total_debit": float(r[7]) if r[7] else 0, "total_credit": float(r[8]) if r[8] else 0, "is_posted": r[9], "created_by": r[10], "lines": [{"id": l[0], "account_id": l[1], "account_code": l[2], "account_name": l[3], "debit": float(l[4]) if l[4] else 0, "credit": float(l[5]) if l[5] else 0, "description": l[6], "cost_center_id": l[7]} for l in lines]}


@router.post("/journal", status_code=201)
async def create_journal_entry(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); lines = body.get("lines", []); total_debit = sum(l.get("debit", 0) for l in lines); total_credit = sum(l.get("credit", 0) for l in lines)
    if not lines or abs(total_debit - total_credit) > 0.01: raise HTTPException(400, detail=f"Entry not balanced: debit={total_debit}, credit={total_credit}")
    for line in lines:
        aid = line.get("account_id")
        if not aid: raise HTTPException(400, detail="account_id required")
        if not db.execute(text("SELECT 1 FROM dbp_accounts WHERE id = :aid AND tenant_id = :tid"), {"aid": aid, "tid": tid}).fetchone(): raise HTTPException(404, detail="Account not found")
        if float(line.get("debit", 0) or 0) < 0 or float(line.get("credit", 0) or 0) < 0 or (float(line.get("debit", 0) or 0) == 0 and float(line.get("credit", 0) or 0) == 0): raise HTTPException(400, detail="Invalid journal line")
    eid = str(uuid.uuid4()); now = datetime.now(timezone.utc)
    db.execute(text("INSERT INTO dbp_journal_entries (id, tenant_id, company_id, entry_number, entry_date, entry_type, description, reference, status, total_debit, total_credit, is_posted, created_by, created_at) VALUES (:id, :tid, :cid, :en, :ed, :et, :desc, :ref, 'draft', :td, :tc, false, :cb, :now)"), {"id": eid, "tid": tid, "cid": tid, "en": f"JE-{eid[:8].upper()}", "ed": body.get("entry_date", now), "et": body.get("entry_type", "general"), "desc": body.get("description", ""), "ref": body.get("reference"), "td": total_debit, "tc": total_credit, "cb": user.get("id"), "now": now})
    for i, line in enumerate(lines):
        db.execute(text("INSERT INTO dbp_journal_lines (id, journal_entry_id, account_id, debit, credit, currency_code, description, cost_center_id, line_order, created_at) VALUES (:id, :eid, :aid, :dr, :cr, :cur, :desc, :cc, :lo, :now)"), {"id": str(uuid.uuid4()), "eid": eid, "aid": line.get("account_id"), "dr": line.get("debit", 0), "cr": line.get("credit", 0), "cur": line.get("currency_code", "SAR"), "desc": line.get("description"), "cc": line.get("cost_center_id"), "lo": i, "now": now})
    db.commit(); return {"id": eid, "message": "Journal entry created"}


@router.post("/journal/{entry_id}/post")
async def post_journal_entry(entry_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    existing = db.execute(text("SELECT id, status FROM dbp_journal_entries WHERE id = :id AND tenant_id = :tid FOR UPDATE"), {"id": entry_id, "tid": tid}).fetchone()
    if not existing: raise HTTPException(404, detail="Journal entry not found")
    if existing[1] == "posted": raise HTTPException(400, detail="Already posted")
    lines = db.execute(text("SELECT account_id, debit, credit FROM dbp_journal_lines WHERE journal_entry_id = :eid"), {"eid": entry_id}).fetchall()
    if not lines: raise HTTPException(400, detail="Journal entry has no lines")
    for aid, dr, cr in lines:
        if not db.execute(text("SELECT 1 FROM dbp_accounts WHERE id = :aid AND tenant_id = :tid"), {"aid": aid, "tid": tid}).fetchone(): raise HTTPException(403, detail="Journal line account is outside tenant")
        db.execute(text("UPDATE dbp_accounts SET current_balance = current_balance + :dr - :cr WHERE id = :aid AND tenant_id = :tid"), {"aid": aid, "dr": float(dr or 0), "cr": float(cr or 0), "tid": tid})
    now = datetime.now(timezone.utc)
    db.execute(text("UPDATE dbp_journal_entries SET status = 'posted', is_posted = true, posted_at = :now WHERE id = :id AND tenant_id = :tid"), {"id": entry_id, "now": now, "tid": tid})
    db.commit(); return {"message": "Journal entry posted"}


@router.post("/journal/{entry_id}/reverse")
async def reverse_journal_entry(entry_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user)
    existing = db.execute(text("SELECT id, status FROM dbp_journal_entries WHERE id = :id AND tenant_id = :tid FOR UPDATE"), {"id": entry_id, "tid": tid}).fetchone()
    if not existing: raise HTTPException(404, detail="Journal entry not found")
    if existing[1] == "reversed": raise HTTPException(400, detail="Already reversed")
    if existing[1] == "posted":
        lines = db.execute(text("SELECT account_id, debit, credit FROM dbp_journal_lines WHERE journal_entry_id = :eid"), {"eid": entry_id}).fetchall()
        for aid, dr, cr in lines:
            if not db.execute(text("SELECT 1 FROM dbp_accounts WHERE id = :aid AND tenant_id = :tid"), {"aid": aid, "tid": tid}).fetchone(): raise HTTPException(403, detail="Journal line account is outside tenant")
            db.execute(text("UPDATE dbp_accounts SET current_balance = current_balance - :dr + :cr WHERE id = :aid AND tenant_id = :tid"), {"aid": aid, "dr": float(dr or 0), "cr": float(cr or 0), "tid": tid})
    db.execute(text("UPDATE dbp_journal_entries SET status = 'reversed', is_posted = false WHERE id = :id AND tenant_id = :tid"), {"id": entry_id, "tid": tid}); db.commit()
    return {"message": "Journal entry reversed"}


@router.get("/reports/trial-balance")
async def trial_balance(as_of_date: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); rows = db.execute(text("SELECT code, name_en, account_type, current_balance FROM dbp_accounts WHERE tenant_id = :tid AND is_active = true ORDER BY code"), {"tid": tid}).fetchall()
    accounts = [{"code": r[0], "name": r[1], "account_type": r[2], "balance": float(r[3]) if r[3] else 0} for r in rows]
    return {"accounts": accounts, "total_debit": sum(a["balance"] for a in accounts if a["balance"] > 0 and a["account_type"] in ("asset", "expense")), "total_credit": sum(abs(a["balance"]) for a in accounts if a["balance"] < 0 and a["account_type"] in ("liability", "equity", "revenue"))}


@router.get("/reports/income-statement")
async def income_statement(start_date: str | None = None, end_date: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); rows = db.execute(text("SELECT code, name_en, account_type, current_balance FROM dbp_accounts WHERE tenant_id = :tid AND account_type IN ('revenue', 'expense') AND is_active = true ORDER BY code"), {"tid": tid}).fetchall()
    revenue = sum(float(r[3]) for r in rows if r[2] == "revenue" and r[3]); expenses = sum(abs(float(r[3])) for r in rows if r[2] == "expense" and r[3])
    return {"revenue": revenue, "expenses": expenses, "net_income": revenue - expenses}


@router.get("/reports/balance-sheet")
async def balance_sheet(as_of_date: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); rows = db.execute(text("SELECT code, name_en, account_type, current_balance FROM dbp_accounts WHERE tenant_id = :tid AND account_type IN ('asset', 'liability', 'equity') AND is_active = true ORDER BY code"), {"tid": tid}).fetchall()
    assets = sum(float(r[3]) for r in rows if r[2] == "asset" and r[3]); liabilities = sum(abs(float(r[3])) for r in rows if r[2] == "liability" and r[3]); equity = sum(abs(float(r[3])) for r in rows if r[2] == "equity" and r[3])
    return {"assets": assets, "liabilities": liabilities, "equity": equity}


@router.get("/reports/cash-flow")
async def cash_flow(start_date: str | None = None, end_date: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _tenant(user)
    return {"operating": 0, "investing": 0, "financing": 0, "net_cash": 0}


@router.get("/reports/profit-and-loss")
async def profit_and_loss(start_date: str | None = None, end_date: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = _tenant(user); rows = db.execute(text("SELECT code, name_en, account_type, current_balance FROM dbp_accounts WHERE tenant_id = :tid AND account_type IN ('revenue', 'expense') AND is_active = true ORDER BY code"), {"tid": tid}).fetchall()
    revenue = sum(float(r[3]) for r in rows if r[2] == "revenue" and r[3]); expenses = sum(abs(float(r[3])) for r in rows if r[2] == "expense" and r[3])
    return {"revenue": revenue, "cogs": 0, "gross_profit": revenue, "operating_expenses": expenses, "net_income": revenue - expenses}
