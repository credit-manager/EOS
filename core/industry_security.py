"""
Industry Security Layer — Shared Hardening for All Industry Templates
=====================================================================
Extracted from P70.3A Construction hardening. Every industry template
(Construction, Trading, Retail, Restaurant, Manufacturing, Services)
inherits this foundation without re-implementing security logic.

Provides:
- H1: Tenant Isolation (query filtering)
- H2: RBAC (role-based permission checks)
- H3: Integrity (journal balancing, input validation)
- H4: Concurrency (SELECT FOR UPDATE helpers)
- H5: Audit Trail (mutation logging)
- H6: Error Handling (standardized responses)
- H7: Journal Posting (balanced debit/credit)
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

# ═══════════════════════════════════════════════════
# CORE UTILITIES
# ═══════════════════════════════════════════════════

def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


def get_company_id(db: Session, tenant_id: str) -> str:
    """Get the primary company_id for a tenant."""
    row = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id=:t LIMIT 1"),
                     {"t": tenant_id}).fetchone()
    return row[0] if row else ""


def get_tenant_config(db: Session, tenant_id: str, key: str, default=None):
    """
    Read a tenant-scoped configuration value from dbp_system_config.

    Fixed H11/H12/H13: replace hardcoded VAT/labor settings with values
    that can be configured per tenant. Falls back to `default` when the
    key is not set.
    """
    if not tenant_id:
        return default
    try:
        row = db.execute(text(
            "SELECT config_value FROM dbp_system_config "
            "WHERE tenant_id=:t AND config_key=:k LIMIT 1"
        ), {"t": tenant_id, "k": key}).fetchone()
    except Exception:
        return default
    if not row:
        return default
    val = row[0]
    if isinstance(val, dict) and "value" in val:
        return val["value"]
    return val or default


# ═══════════════════════════════════════════════════
# H2: RBAC — Role-Based Access Control
# ═══════════════════════════════════════════════════

# Role hierarchy: platform_owner > admin > manager > accountant > user > viewer
ROLE_HIERARCHY = {
    "platform_owner": 100,
    "admin": 90,
    "manager": 70,
    "accountant": 60,
    "user": 40,
    "viewer": 20,
}

# Permission matrix: which roles can do what
PERMISSION_MATRIX = {
    "read":      ["viewer", "user", "accountant", "manager", "admin", "platform_owner"],
    "create":    ["user", "accountant", "manager", "admin", "platform_owner"],
    "update":    ["user", "accountant", "manager", "admin", "platform_owner"],
    "delete":    ["manager", "admin", "platform_owner"],
    "approve":   ["manager", "admin", "platform_owner"],
    "export":    ["accountant", "manager", "admin", "platform_owner"],
    "settings":  ["admin", "platform_owner"],
}


def check_permission(user: dict, action: str):
    """
    Check if user has permission for the given action.
    Raises HTTPException 403 if not authorized.
    """
    roles = user.get("roles", [])
    if not roles:
        raise HTTPException(403, detail="No roles assigned")

    # Wildcard admin check
    if "platform_owner" in roles or "admin" in roles:
        return True

    allowed_roles = PERMISSION_MATRIX.get(action, [])
    for role in roles:
        if role in allowed_roles:
            return True

    raise HTTPException(403, detail=f"Insufficient permissions for: {action}")


# ═══════════════════════════════════════════════════
# H1: TENANT ISOLATION — Query Filtering
# ═══════════════════════════════════════════════════

def tenant_filter(user: dict) -> str:
    """Returns the tenant_id for filtering queries."""
    return user.get("tenant_id", "")


def verify_tenant_access(user: dict, record_tenant_id: str):
    """Verify a record belongs to the user's tenant."""
    if user.get("tenant_id", "") != record_tenant_id:
        raise HTTPException(403, detail="Access denied: cross-tenant violation")


# ═══════════════════════════════════════════════════
# H5: AUDIT TRAIL — Mutation Logging
# ═══════════════════════════════════════════════════

def audit_log(db: Session, tenant_id: str, user_id: str, action: str,
              entity_type: str, entity_id: str,
              old_values: dict | None = None, new_values: dict | None = None):
    """Log an audit entry for any mutation."""
    db.execute(
        text("INSERT INTO dbp_construction_audit "
             "(id, tenant_id, user_id, action, entity_type, entity_id, old_values, new_values, created_at) "
             "VALUES (:id, :tid, :uid, :act, :et, :eid, :old, :new, :now)"),
        {"id": uid(), "tid": tenant_id, "uid": user_id, "act": action,
         "et": entity_type, "eid": entity_id,
         "old": json.dumps(old_values or {}), "new": json.dumps(new_values or {}),
         "now": now()},
    )


# ═══════════════════════════════════════════════════
# H7: JOURNAL POSTING — Balanced Debit/Credit
# ═══════════════════════════════════════════════════

def post_journal(db: Session, tenant_id: str, company_id: str,
                 journal_type: str, description: str,
                 lines: list[dict[str, Any]],
                 ref_entity: str = "", ref_id: str = "") -> str:
    """
    Post a journal entry. Enforces balanced debits=credits.
    Returns the journal entry ID.
    """
    jid = uid()
    entry_number = f"JE-{now().strftime('%Y%m%d')}-{jid[:8].upper()}"
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)

    if abs(total_debit - total_credit) > Decimal("0.01"):
        raise HTTPException(400, detail=f"Journal not balanced: debit={total_debit}, credit={total_credit}")

    db.execute(
        text("INSERT INTO dbp_journal_entries (id, tenant_id, company_id, entry_number, entry_date, "
             "entry_type, description, total_debit, total_credit, status, is_posted, created_by, created_at) "
             "VALUES (:id, :tid, :cid, :num, :date, :etype, :desc, :dr, :cr, 'posted', true, :by, :now)"),
        {"id": jid, "tid": tenant_id, "cid": company_id or None, "num": entry_number,
         "date": now().date(), "etype": journal_type, "desc": description,
         "dr": total_debit, "cr": total_credit, "by": ref_entity, "now": now()},
    )
    for i, line in enumerate(lines):
        lid = uid()
        db.execute(
            text("INSERT INTO dbp_journal_lines (id, journal_entry_id, account_id, description, "
                 "debit, credit, cost_center_id, line_order, created_at) "
                 "VALUES (:id, :jid, :acct, :desc, :dr, :cr, :cc, :ord, :now)"),
            {"id": lid, "jid": jid, "acct": line.get("account_code", ""),
             "desc": line.get("description", ""), "dr": line.get("debit", 0),
             "cr": line.get("credit", 0), "cc": line.get("cost_center", ""),
             "ord": i + 1, "now": now()},
        )
        # P80.5D FIX: Keep the GL in sync. Posting a journal must flow into
        # dbp_accounts.current_balance, which the trial balance / income
        # statement / balance sheet reports read directly. Previously this
        # path inserted lines marked posted but never updated current_balance,
        # so journals posted here silently disappeared from reported balances.
        # Journal lines carry the ACCOUNT CODE (primary key of a trading entry);
        # map it to dbp_accounts.code scoped by tenant (same scope as the reports).
        dr = Decimal(str(line.get("debit", 0)))
        cr = Decimal(str(line.get("credit", 0)))
        if line.get("account_code"):
            db.execute(
                text("UPDATE dbp_accounts SET current_balance = current_balance + :dr - :cr "
                     "WHERE code = :code AND tenant_id = :tid"),
                {"code": line.get("account_code", ""), "dr": dr, "cr": cr, "tid": tenant_id},
            )
    return jid


# ═══════════════════════════════════════════════════
# H4: CONCURRENCY — Atomic Stock Operations
# ═══════════════════════════════════════════════════

def atomic_stock_issue(db: Session, tenant_id: str, item_id: str,
                       qty: float, warehouse_id: str = "default",
                       stock_table: str = "dbp_construction_stock",
                       item_column: str = "item_code"):
    """
    Atomically issue stock with row-level locking.
    Returns (stock_id, unit_cost) or raises.
    """
    stock = db.execute(
        text(f"SELECT id, on_hand, unit_cost FROM {stock_table} "
             f"WHERE tenant_id=:t AND {item_column}=:ic AND warehouse_id=:w FOR UPDATE"),
        {"t": tenant_id, "ic": item_id, "w": warehouse_id},
    ).fetchone()
    if not stock:
        raise HTTPException(404, detail=f"Item not found: {item_id}")
    available = Decimal(str(stock[1] or 0))
    if available < Decimal(str(qty)):
        raise HTTPException(400, detail=f"Insufficient stock: {item_id} has {available}, need {qty}")
    new_qty = available - Decimal(str(qty))
    db.execute(text(f"UPDATE {stock_table} SET on_hand=:q WHERE id=:sid"),
               {"q": new_qty, "sid": stock[0]})
    return stock[0], float(stock[2] or 0)


def atomic_stock_receive(db: Session, tenant_id: str, item_id: str,
                         qty: float, price: float, warehouse_id: str = "default",
                         stock_table: str = "dbp_construction_stock",
                         item_column: str = "item_code"):
    """
    Atomically receive stock with row-level locking and weighted average cost.
    """
    existing = db.execute(
        text(f"SELECT id, on_hand, unit_cost FROM {stock_table} "
             f"WHERE tenant_id=:t AND {item_column}=:ic AND warehouse_id=:w FOR UPDATE"),
        {"t": tenant_id, "ic": item_id, "w": warehouse_id},
    ).fetchone()
    total_cost = Decimal(str(qty)) * Decimal(str(price))
    if existing:
        old_qty = Decimal(str(existing[1] or 0))
        new_qty = old_qty + Decimal(str(qty))
        old_cost = Decimal(str(existing[2] or 0))
        new_cost = ((old_qty * old_cost) + total_cost) / new_qty if new_qty > 0 else Decimal(str(price))
        db.execute(text(f"UPDATE {stock_table} SET on_hand=:q, unit_cost=:uc WHERE id=:sid"),
                   {"q": new_qty, "uc": new_cost, "sid": existing[0]})
        return existing[0]
    else:
        sid = uid()
        db.execute(text(f"INSERT INTO {stock_table} "
                        f"(id, tenant_id, {item_column}, warehouse_id, on_hand, reserved, unit_cost, created_at) "
                        "VALUES (:id, :t, :ic, :w, :q, 0, :uc, :now)"),
                   {"id": sid, "t": tenant_id, "ic": item_id, "w": warehouse_id,
                    "q": qty, "uc": price, "now": now()})
        return sid


# ═══════════════════════════════════════════════════
# H3: SEQUENCE GENERATORS (Unique per tenant)
# ═══════════════════════════════════════════════════

def generate_sequence(db: Session, tenant_id: str, prefix: str, table: str,
                      column: str = "number", entity_type: str | None = None) -> str:
    """
    Generate a unique sequential number per tenant.

    Fixed H7: Previously used COUNT(*)+1 which is racy under concurrency.
    Now uses an atomic per-tenant counter in the number_sequences table so
    concurrent callers never receive the same sequence number.
    E.g., SO-202608-A1B2C3 for Sales Orders.
    """
    seq_name = f"{prefix}-{entity_type or table}"
    # Atomic increment of the per-tenant counter
    row = db.execute(
        text(
            "INSERT INTO number_sequences "
            "(id, tenant_id, name, prefix, current_number, increment_by, padding, entity_type, is_active) "
            "VALUES (:id, :t, :name, :prefix, 1, 1, 0, :et, true) "
            "ON CONFLICT (tenant_id, name) DO UPDATE "
            "SET current_number = number_sequences.current_number + number_sequences.increment_by "
            "RETURNING current_number, prefix"
        ),
        {"id": uid(), "t": tenant_id, "name": seq_name, "prefix": prefix, "et": entity_type or table},
    ).fetchone()
    seq = int(row[0]) if row else 1
    used_prefix = row[1] if row and row[1] else prefix
    suffix = uid()[:6].upper()
    return f"{used_prefix}-{now().strftime('%Y%m')}-{seq}-{suffix}"


# ═══════════════════════════════════════════════════
# H6: STANDARDIZED RESPONSES
# ═══════════════════════════════════════════════════

def success_response(message: str, data: dict | None = None) -> dict:
    """Standard success response."""
    resp = {"status": "success", "message": message}
    if data:
        resp["data"] = data
    return resp


def list_response(data: list, total: int, page: int = 1, page_size: int = 50) -> dict:
    """Standard list response with pagination."""
    return {"data": data, "total": total, "page": page, "page_size": page_size}


def error_response(status_code: int, message: str) -> HTTPException:
    """Standard error response."""
    return HTTPException(status_code, detail=message)
