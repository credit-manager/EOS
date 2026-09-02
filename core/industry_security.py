"""Shared security and API helpers for industry templates."""
import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())


def success_response(message: str = "Success", data: Any = None) -> dict:
    return {"success": True, "message": message, "data": data}


def list_response(data: List[Any], total: int, page: int = 1, page_size: int = 50) -> dict:
    page, page_size, total = max(int(page or 1), 1), max(int(page_size or 50), 1), max(int(total or 0), 0)
    return {"success": True, "data": data, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


def error_response(message: str = "Request failed", status_code: int = 400, details: Any = None) -> dict:
    payload = {"success": False, "message": message}
    if details is not None: payload["details"] = details
    return payload


def get_company_id(db: Session, tenant_id: str) -> str:
    row = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id=:t LIMIT 1"), {"t": tenant_id}).fetchone()
    return row[0] if row else ""


def get_tenant_config(db: Session, tenant_id: str, key: str, default=None):
    if not tenant_id: return default
    try:
        row = db.execute(text("SELECT config_value FROM dbp_system_config WHERE tenant_id=:t AND config_key=:k LIMIT 1"), {"t": tenant_id, "k": key}).fetchone()
    except Exception: return default
    if not row: return default
    val = row[0]
    return val.get("value") if isinstance(val, dict) and "value" in val else (val or default)

ROLE_HIERARCHY = {"platform_owner":100,"admin":90,"manager":70,"accountant":60,"user":40,"viewer":20}
PERMISSION_MATRIX = {"read":["viewer","user","accountant","manager","admin","platform_owner"],"create":["user","accountant","manager","admin","platform_owner"],"update":["user","accountant","manager","admin","platform_owner"],"delete":["manager","admin","platform_owner"],"approve":["manager","admin","platform_owner"],"export":["accountant","manager","admin","platform_owner"],"settings":["admin","platform_owner"]}


def check_permission(user: dict, action: str):
    roles = user.get("roles", [])
    if not roles: raise HTTPException(403, detail="No roles assigned")
    if "platform_owner" in roles or "admin" in roles or any(r in PERMISSION_MATRIX.get(action, []) for r in roles): return True
    raise HTTPException(403, detail=f"Insufficient permissions for: {action}")


def tenant_filter(user: dict) -> str: return user.get("tenant_id", "")
def verify_tenant_access(user: dict, record_tenant_id: str):
    if user.get("tenant_id", "") != record_tenant_id: raise HTTPException(403, detail="Access denied: cross-tenant violation")


def audit_log(db: Session, tenant_id: str, user_id: str, action: str, entity_type: str, entity_id: str, old_values: dict = None, new_values: dict = None):
    db.execute(text("INSERT INTO dbp_construction_audit (id, tenant_id, user_id, action, entity_type, entity_id, old_values, new_values, created_at) VALUES (:id,:tid,:uid,:act,:et,:eid,:old,:new,:now)"), {"id":uid(),"tid":tenant_id,"uid":user_id,"act":action,"et":entity_type,"eid":entity_id,"old":json.dumps(old_values or {}),"new":json.dumps(new_values or {}),"now":now()})


def post_journal(db: Session, tenant_id: str, company_id: str, journal_type: str, description: str, lines: List[Dict[str, Any]], ref_entity: str = "", ref_id: str = "") -> str:
    if not lines: raise HTTPException(400, detail="Journal must contain at least one line")
    jid, entry_number = uid(), f"JE-{now().strftime('%Y%m%d')}-{uid()[:8].upper()}"
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines); total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)
    if abs(total_debit-total_credit) > Decimal("0.001"): raise HTTPException(400, detail=f"Journal not balanced: debit={total_debit}, credit={total_credit}")
    db.execute(text("INSERT INTO dbp_journal_entries (id,tenant_id,company_id,entry_number,entry_date,entry_type,description,total_debit,total_credit,status,is_posted,created_by,created_at) VALUES (:id,:tid,:cid,:num,:date,:etype,:desc,:dr,:cr,'posted',true,:by,:now)"), {"id":jid,"tid":tenant_id,"cid":company_id,"num":entry_number,"date":now().date(),"etype":journal_type,"desc":description,"dr":total_debit,"cr":total_credit,"by":ref_entity,"now":now()})
    for i,line in enumerate(lines):
        code=str(line.get("account_code","")).strip()
        if not code: raise HTTPException(400, detail="Journal line account_code is required")
        account=db.execute(text("SELECT id FROM dbp_accounts WHERE code=:code AND tenant_id=:tid AND company_id=:cid AND is_active=true"), {"code":code,"tid":tenant_id,"cid":company_id}).fetchone()
        if not account: raise HTTPException(400, detail=f"Account not found for tenant/company: {code}")
        db.execute(text("INSERT INTO dbp_journal_lines (id,journal_entry_id,account_id,description,debit,credit,cost_center_id,line_order,created_at) VALUES (:id,:jid,:acct,:desc,:dr,:cr,:cc,:ord,:now)"), {"id":uid(),"jid":jid,"acct":account[0],"desc":line.get("description",""),"dr":line.get("debit",0),"cr":line.get("credit",0),"cc":line.get("cost_center_id") or line.get("cost_center"),"ord":i+1,"now":now()})
        db.execute(text("UPDATE dbp_accounts SET current_balance=current_balance+:dr-:cr WHERE id=:aid AND tenant_id=:tid AND company_id=:cid"), {"aid":account[0],"dr":Decimal(str(line.get("debit",0))),"cr":Decimal(str(line.get("credit",0))),"tid":tenant_id,"cid":company_id})
    return jid


def atomic_stock_issue(db: Session, tenant_id: str, item_id: str, qty: float, warehouse_id: str = "default", stock_table: str = "dbp_construction_stock", item_column: str = "item_code"):
    stock=db.execute(text(f"SELECT id,on_hand,unit_cost FROM {stock_table} WHERE tenant_id=:t AND {item_column}=:ic AND warehouse_id=:w FOR UPDATE"), {"t":tenant_id,"ic":item_id,"w":warehouse_id}).fetchone()
    if not stock: raise HTTPException(404, detail=f"Item not found: {item_id}")
    available=Decimal(str(stock[1] or 0))
    if available < Decimal(str(qty)): raise HTTPException(400, detail=f"Insufficient stock: {item_id} has {available}, need {qty}")
    db.execute(text(f"UPDATE {stock_table} SET on_hand=:q WHERE id=:sid"), {"q":available-Decimal(str(qty)),"sid":stock[0]})
    return stock[0], float(stock[2] or 0)


def atomic_stock_receive(db: Session, tenant_id: str, item_id: str, qty: float, price: float, warehouse_id: str = "default", stock_table: str = "dbp_construction_stock", item_column: str = "item_code"):
    existing=db.execute(text(f"SELECT id,on_hand,unit_cost FROM {stock_table} WHERE tenant_id=:t AND {item_column}=:ic AND warehouse_id=:w FOR UPDATE"), {"t":tenant_id,"ic":item_id,"w":warehouse_id}).fetchone()
    total_cost=Decimal(str(qty))*Decimal(str(price))
    if existing:
        old_qty,old_cost=Decimal(str(existing[1] or 0)),Decimal(str(existing[2] or 0)); new_qty=old_qty+Decimal(str(qty)); new_cost=((old_qty*old_cost)+total_cost)/new_qty if new_qty else Decimal("0")
        db.execute(text(f"UPDATE {stock_table} SET on_hand=:q,unit_cost=:uc WHERE id=:sid"), {"q":new_qty,"uc":new_cost,"sid":existing[0]}); return existing[0],float(new_cost)
    sid=uid(); db.execute(text(f"INSERT INTO {stock_table} (id,tenant_id,{item_column},warehouse_id,on_hand,unit_cost) VALUES (:id,:t,:ic,:w,:q,:uc)"), {"id":sid,"t":tenant_id,"ic":item_id,"w":warehouse_id,"q":qty,"uc":price}); return sid,float(price)
