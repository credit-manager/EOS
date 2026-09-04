"""
P70.5 Retail ERP Professional — API
====================================
POS, Cash Management, Loyalty, Promotions, Analytics.
Commerce operations delegated to core/commerce_engine.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from core.auth import get_current_user
from core.commerce_engine import (
    get_item as _ce_get_item,
)
from core.commerce_engine import (
    get_item_by_barcode as _ce_get_item_by_barcode,
)
from core.commerce_engine import (
    get_stock as _ce_get_stock,
)
from core.industry_security import (
    atomic_stock_issue,
    atomic_stock_receive,
    audit_log,
    check_permission,
    get_company_id,
    get_tenant_config,
    list_response,
    now,
    post_journal,
    success_response,
    uid,
)
from database import get_db

router = APIRouter(prefix="/retail", tags=["Retail POS"])


# ═══════════════════════════════════════════════════
# HELPERS (delegated to Commerce Engine)
# ═══════════════════════════════════════════════════

def _get_item(db, tenant_id, item_id):
    return _ce_get_item(db, tenant_id, item_id)


def _get_stock(db, tenant_id, item_id, warehouse_id):
    stk = _ce_get_stock(db, tenant_id, item_id, warehouse_id)
    return stk.get("on_hand", 0)


def _get_active_session(db, tenant_id, register_id):
    row = db.execute(text("SELECT id, cashier_id, opening_amount FROM dbp_retail_cash_sessions "
                          "WHERE tenant_id=:t AND register_id=:r AND status='open' "
                          "ORDER BY opened_at DESC LIMIT 1"),
                     {"t": tenant_id, "r": register_id}).fetchone()
    if not row:
        raise HTTPException(400, detail="No open cash session. Open the register first.")
    return {"id": row[0], "cashier_id": row[1], "opening_amount": float(row[2] or 0)}


# ═══════════════════════════════════════════════════
# MASTER DATA: Registers & Cashiers
# ═══════════════════════════════════════════════════

class RegisterCreate(BaseModel):
    register_code: str
    name: str
    warehouse_id: str

@router.post("/registers")
def create_register(body: RegisterCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_retail_registers WHERE tenant_id=:t AND register_code=:rc"),
                          {"t": t, "rc": body.register_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Register code already exists")
    rid = uid()
    try:
        db.execute(text("INSERT INTO dbp_retail_registers (id,tenant_id,register_code,name,warehouse_id) "
                        "VALUES (:id,:t,:rc,:n,:wid)"),
                   {"id": rid, "t": t, "rc": body.register_code, "n": body.name, "wid": body.warehouse_id})
        audit_log(db, t, user["id"], "create", "register", rid, new_values={"code": body.register_code})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=f"Register creation failed: {e!s}")
    return success_response("Register created", {"id": rid})


class CashierCreate(BaseModel):
    name: str
    pin: str | None = None
    register_id: str | None = None

@router.post("/cashiers")
def create_cashier(body: CashierCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    cid = uid()
    db.execute(text("INSERT INTO dbp_retail_cashiers (id,tenant_id,user_id,name,pin,register_id) "
                    "VALUES (:id,:t,:uid,:n,:pin,:rid)"),
               {"id": cid, "t": t, "uid": user["id"], "n": body.name,
                "pin": body.pin, "rid": body.register_id})
    audit_log(db, t, user["id"], "create", "cashier", cid, new_values={"name": body.name})
    db.commit()
    return success_response("Cashier created", {"id": cid})


@router.get("/registers")
def list_registers(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    try:
        rows = db.execute(text("SELECT id,register_code,name,warehouse_id,status FROM dbp_retail_registers "
                               "WHERE tenant_id=:t ORDER BY created_at"), {"t": t}).fetchall()
        data = [{"id": r[0], "code": r[1], "name": r[2], "warehouse_id": r[3], "status": r[4]} for r in rows]
    except Exception as e:
        raise HTTPException(500, detail=f"List registers failed: {e!s}")
    return list_response(data, len(data))


@router.get("/cashiers")
def list_cashiers(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,register_id,status FROM dbp_retail_cashiers "
                           "WHERE tenant_id=:t ORDER BY created_at"), {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "register_id": r[2], "status": r[3]} for r in rows]
    return list_response(data, len(data))


@router.get("/registers/{reg_id}")
def get_register(reg_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,register_code,name,warehouse_id,status "
                          "FROM dbp_retail_registers WHERE id=:id AND tenant_id=:t"),
                     {"id": reg_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Register not found")
    return success_response("Register found", {
        "id": row[0], "code": row[1], "name": row[2], "warehouse_id": row[3], "status": row[4]})


@router.get("/cashiers/{cashier_id}")
def get_cashier(cashier_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,name,register_id,status "
                          "FROM dbp_retail_cashiers WHERE id=:id AND tenant_id=:t"),
                     {"id": cashier_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Cashier not found")
    return success_response("Cashier found", {
        "id": row[0], "name": row[1], "register_id": row[2], "status": row[3]})


# ═══════════════════════════════════════════════════
# BARCODE SEARCH (POS expects barcode lookup)
# ═══════════════════════════════════════════════════

@router.get("/items/barcode/{barcode}")
def get_item_by_barcode(barcode: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    item = _ce_get_item_by_barcode(db, t, barcode)
    return success_response("Item found", {
        "id": item["id"], "item_code": item.get("item_code", ""),
        "name": item["name"],
        "selling_price": item["selling_price"], "cost_price": item["cost_price"],
        "barcode": item.get("barcode", ""), "unit": item.get("unit", "piece"),
    })


# ═══════════════════════════════════════════════════
# POS: CREATE SALE
# ═══════════════════════════════════════════════════

class POSSaleLine(BaseModel):
    item_id: str
    qty: float = Field(ge=0.01)
    unit_price: float = Field(ge=0)
    discount_pct: float = Field(default=0, ge=0, le=100)

class POSSaleCreate(BaseModel):
    register_id: str
    cashier_id: str
    customer_id: str | None = None
    payment_method: str = "cash"
    paid_amount: float = Field(ge=0)
    lines: list[POSSaleLine]
    loyalty_points_redeemed: int = Field(default=0, ge=0)
    notes: str | None = None


@router.post("/pos/sales")
def create_pos_sale(body: POSSaleCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    valid_payments = ["cash", "card", "mobile", "credit", "loyalty"]
    if body.payment_method not in valid_payments:
        raise HTTPException(400, detail=f"Invalid payment method: {body.payment_method}. Use: {valid_payments}")

    if not body.lines:
        raise HTTPException(400, detail="Sale must have at least one item")

    for l in body.lines:
        if l.qty <= 0:
            raise HTTPException(400, detail=f"Invalid qty: {l.qty}")
        if l.unit_price < 0:
            raise HTTPException(400, detail=f"Invalid price: {l.unit_price}")

    _get_active_session(db, t, body.register_id)

    reg = db.execute(text("SELECT warehouse_id FROM dbp_retail_registers WHERE id=:r AND tenant_id=:t"),
                     {"r": body.register_id, "t": t}).fetchone()
    warehouse_id = reg[0] if reg else "default"

    sale_id = uid()
    sale_num = f"POS-{now().strftime('%Y%m%d')}-{sale_id[:6].upper()}"

    subtotal = 0.0
    total_tax = 0.0
    total_discount = 0.0

    for l in body.lines:
        item = _get_item(db, t, l.item_id)
        line_discount = l.unit_price * l.qty * (l.discount_pct / 100)
        line_total = l.unit_price * l.qty - line_discount
        subtotal += line_total
        total_discount += line_discount

    # Fixed H11: VAT rate is now configurable per tenant (default 15%).
    tax_rate = float(get_tenant_config(db, t, "vat_rate", 15.0))
    total_tax = subtotal * (tax_rate / 100)
    grand_total = subtotal + total_tax

    if body.paid_amount < grand_total:
        raise HTTPException(400, detail=f"Paid {body.paid_amount} < total {grand_total:.2f}")

    change = body.paid_amount - grand_total
    points_earned = int(subtotal // 10)

    db.execute(text("INSERT INTO dbp_retail_pos_sales "
                    "(id,tenant_id,sale_number,register_id,cashier_id,customer_id,"
                    "subtotal,tax_rate,tax_amount,discount_amount,total,paid_amount,change_amount,"
                    "payment_method,loyalty_points_earned,loyalty_points_redeemed,status) "
                    "VALUES (:id,:t,:sn,:reg,:ca,:cu,:sub,:tr,:ta,:da,:tot,:pa,:ch,:pm,:lpe,:lpr,'completed')"),
               {"id": sale_id, "t": t, "sn": sale_num, "reg": body.register_id,
                "ca": body.cashier_id, "cu": body.customer_id,
                "sub": subtotal, "tr": tax_rate, "ta": total_tax,
                "da": total_discount, "tot": grand_total,
                "pa": body.paid_amount, "ch": change, "pm": body.payment_method,
                "lpe": points_earned, "lpr": body.loyalty_points_redeemed})

    for l in body.lines:
        item = _get_item(db, t, l.item_id)
        lid = uid()
        line_discount = l.unit_price * l.qty * (l.discount_pct / 100)
        line_total = l.unit_price * l.qty - line_discount

        db.execute(text("INSERT INTO dbp_retail_pos_lines "
                        "(id,tenant_id,sale_id,item_id,barcode,description,qty,unit_price,"
                        "cost_price,discount_pct,discount_amount,line_total) "
                        "VALUES (:id,:t,:si,:iid,:bc,:desc,:qty,:up,:cp,:dd,:da,:lt)"),
                   {"id": lid, "t": t, "si": sale_id, "iid": l.item_id,
                    "bc": item.get("barcode", ""), "desc": item["name"],
                    "qty": l.qty, "up": l.unit_price, "cp": item["cost_price"],
                    "dd": l.discount_pct, "da": line_discount, "lt": line_total})

        atomic_stock_issue(db, t, l.item_id, l.qty, warehouse_id,
                           stock_table="dbp_commerce_stock", item_column="item_id")

    company_id = get_company_id(db, t)

    cogs_total = 0
    for l in body.lines:
        item = _get_item(db, t, l.item_id)
        cogs_total += item["cost_price"] * l.qty

    post_journal(db, t, company_id, "pos_sale", f"POS Sale {sale_num}",
                 [{"account_code": "1000", "description": "Cash", "debit": grand_total},
                  {"account_code": "4000", "description": "Revenue", "credit": subtotal},
                  {"account_code": "2100", "description": "Tax Payable", "credit": total_tax},
                  {"account_code": "5100", "description": "COGS", "debit": cogs_total},
                  {"account_code": "1300", "description": "Inventory", "credit": cogs_total}])

    if body.customer_id and points_earned > 0:
        acct = db.execute(text("SELECT id FROM dbp_retail_loyalty_accounts "
                               "WHERE tenant_id=:t AND customer_id=:cu"),
                          {"t": t, "cu": body.customer_id}).fetchone()
        if acct:
            db.execute(text("UPDATE dbp_retail_loyalty_accounts "
                            "SET total_points=total_points+:p, available_points=available_points+:p, "
                            "lifetime_spend=lifetime_spend+:s, updated_at=NOW() "
                            "WHERE id=:aid"),
                       {"p": points_earned, "s": subtotal, "aid": acct[0]})
            db.execute(text("INSERT INTO dbp_retail_loyalty_transactions "
                            "(id,tenant_id,account_id,sale_id,transaction_type,points,description) "
                            "VALUES (:id,:t,:aid,:si,'earn',:p,:d)"),
                       {"id": uid(), "t": t, "aid": acct[0], "si": sale_id,
                        "p": points_earned, "d": f"Earned from {sale_num}"})

    if body.loyalty_points_redeemed > 0 and body.customer_id:
        acct = db.execute(text("SELECT id, available_points FROM dbp_retail_loyalty_accounts "
                               "WHERE tenant_id=:t AND customer_id=:cu"),
                          {"t": t, "cu": body.customer_id}).fetchone()
        if acct and acct[1] >= body.loyalty_points_redeemed:
            db.execute(text("UPDATE dbp_retail_loyalty_accounts "
                            "SET redeemed_points=redeemed_points+:r, available_points=available_points-:r, "
                            "updated_at=NOW() WHERE id=:aid"),
                       {"r": body.loyalty_points_redeemed, "aid": acct[0]})
            db.execute(text("INSERT INTO dbp_retail_loyalty_transactions "
                            "(id,tenant_id,account_id,sale_id,transaction_type,points,description) "
                            "VALUES (:id,:t,:aid,:si,'redeem',:p,:d)"),
                       {"id": uid(), "t": t, "aid": acct[0], "si": sale_id,
                        "p": body.loyalty_points_redeemed, "d": f"Redeemed in {sale_num}"})

    audit_log(db, t, user["id"], "create", "pos_sale", sale_id,
              new_values={"total": grand_total, "payment": body.payment_method})
    db.commit()

    return success_response("Sale completed", {
        "id": sale_id, "sale_number": sale_num, "subtotal": subtotal,
        "tax": total_tax, "total": grand_total, "change": change,
        "points_earned": points_earned, "payment_method": body.payment_method,
    })


# ═══════════════════════════════════════════════════
# POS: RETURN
# ═══════════════════════════════════════════════════

class POSReturnLine(BaseModel):
    item_id: str
    qty: float = Field(ge=0.01)
    unit_price: float = Field(ge=0)

class POSReturnCreate(BaseModel):
    original_sale_id: str
    register_id: str
    cashier_id: str
    lines: list[POSReturnLine]
    reason: str | None = None


@router.post("/pos/returns")
def create_pos_return(body: POSReturnCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    _get_active_session(db, t, body.register_id)

    reg = db.execute(text("SELECT warehouse_id FROM dbp_retail_registers WHERE id=:r AND tenant_id=:t"),
                     {"r": body.register_id, "t": t}).fetchone()
    warehouse_id = reg[0] if reg else "default"

    original = db.execute(text("SELECT id,customer_id FROM dbp_retail_pos_sales "
                               "WHERE id=:id AND tenant_id=:t"),
                          {"id": body.original_sale_id, "t": t}).fetchone()
    if not original:
        raise HTTPException(404, detail="Original sale not found")

    ret_id = uid()
    ret_num = f"RET-{now().strftime('%Y%m%d')}-{ret_id[:6].upper()}"
    refund_total = sum(l.unit_price * l.qty for l in body.lines)

    db.execute(text("INSERT INTO dbp_retail_pos_sales "
                    "(id,tenant_id,sale_number,register_id,cashier_id,customer_id,"
                    "subtotal,tax_amount,total,paid_amount,change_amount,"
                    "payment_method,is_return,return_of,status) "
                    "VALUES (:id,:t,:sn,:reg,:ca,:cu,0,0,:tot,:pa,0,'cash',true,:ro,'completed')"),
               {"id": ret_id, "t": t, "sn": ret_num, "reg": body.register_id,
                "ca": body.cashier_id, "cu": original[1],
                "tot": -refund_total, "pa": -refund_total, "ro": body.original_sale_id})

    for l in body.lines:
        lid = uid()
        db.execute(text("INSERT INTO dbp_retail_pos_lines "
                        "(id,tenant_id,sale_id,item_id,qty,unit_price,line_total) "
                        "VALUES (:id,:t,:si,:iid,:qty,:up,:lt)"),
                   {"id": lid, "t": t, "si": ret_id, "iid": l.item_id,
                    "qty": -l.qty, "up": l.unit_price, "lt": -(l.unit_price * l.qty)})
        atomic_stock_receive(db, t, l.item_id, l.qty, l.unit_price, warehouse_id,
                             stock_table="dbp_commerce_stock", item_column="item_id")

    company_id = get_company_id(db, t)

    cogs_refund = 0
    for l in body.lines:
        item = _get_item(db, t, l.item_id)
        cogs_refund += item["cost_price"] * l.qty

    post_journal(db, t, company_id, "pos_return", f"POS Return {ret_num}",
                 [{"account_code": "4000", "description": "Revenue", "debit": refund_total},
                  {"account_code": "1000", "description": "Cash", "credit": refund_total},
                  {"account_code": "5100", "description": "COGS", "credit": cogs_refund},
                  {"account_code": "1300", "description": "Inventory", "debit": cogs_refund}])

    audit_log(db, t, user["id"], "create", "pos_return", ret_id,
              new_values={"refund": refund_total, "reason": body.reason})
    db.commit()
    return success_response("Return processed", {"id": ret_id, "refund": refund_total})


# ═══════════════════════════════════════════════════
# POS: VOID SALE
# ═══════════════════════════════════════════════════

@router.post("/pos/sales/{sale_id}/void")
def void_pos_sale(sale_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    sale = db.execute(text("SELECT id,total,status,payment_method,register_id FROM dbp_retail_pos_sales "
                           "WHERE id=:id AND tenant_id=:t"),
                      {"id": sale_id, "t": t}).fetchone()
    if not sale:
        raise HTTPException(404, detail="Sale not found")
    if sale[2] == "voided":
        raise HTTPException(400, detail="Already voided")

    reg_row = db.execute(text("SELECT warehouse_id FROM dbp_retail_registers WHERE id=:r AND tenant_id=:t"),
                         {"r": sale[4], "t": t}).fetchone()
    void_wh = reg_row[0] if reg_row else "default"

    db.execute(text("UPDATE dbp_retail_pos_sales SET status='voided' "
                    "WHERE id=:id AND tenant_id=:t"), {"id": sale_id, "t": t})

    lines = db.execute(text("SELECT item_id,qty,unit_price,cost_price FROM dbp_retail_pos_lines "
                            "WHERE sale_id=:si AND tenant_id=:t"),
                       {"si": sale_id, "t": t}).fetchall()
    for l in lines:
        atomic_stock_receive(db, t, l[0], abs(float(l[1])), float(l[2]), void_wh,
                             stock_table="dbp_commerce_stock", item_column="item_id")

    company_id = get_company_id(db, t)
    total = abs(float(sale[1]))

    cogs_void = 0
    for l in lines:
        cogs_void += float(l[3] or 0) * abs(float(l[1] or 0))

    post_journal(db, t, company_id, "pos_void", f"Void {sale_id[:8]}",
                 [{"account_code": "1000", "description": "Cash", "credit": total},
                  {"account_code": "4000", "description": "Revenue", "debit": total},
                  {"account_code": "5100", "description": "COGS", "credit": cogs_void},
                  {"account_code": "1300", "description": "Inventory", "debit": cogs_void}])

    audit_log(db, t, user["id"], "void", "pos_sale", sale_id,
              old_values={"total": float(sale[1]), "status": "completed"},
              new_values={"status": "voided"})
    db.commit()
    return success_response("Sale voided", {"id": sale_id, "refund": float(total)})


# ═══════════════════════════════════════════════════
# POS: SUSPEND & RECALL
# ═══════════════════════════════════════════════════

class SuspendCreate(BaseModel):
    register_id: str
    cashier_id: str
    customer_id: str | None = None
    items_json: str
    subtotal: float = 0
    tax_amount: float = 0
    total: float = 0
    notes: str | None = None

@router.post("/pos/suspended")
def suspend_sale(body: SuspendCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sid = uid()
    db.execute(text("INSERT INTO dbp_retail_suspended_sales "
                    "(id,tenant_id,register_id,cashier_id,customer_id,items_json,"
                    "subtotal,tax_amount,total,notes,status) "
                    "VALUES (:id,:t,:reg,:ca,:cu,:ij,:sub,:ta,:tot,:n,'suspended')"),
               {"id": sid, "t": t, "reg": body.register_id, "ca": body.cashier_id,
                "cu": body.customer_id, "ij": body.items_json,
                "sub": body.subtotal, "ta": body.tax_amount, "tot": body.total, "n": body.notes})
    audit_log(db, t, user["id"], "create", "suspended_sale", sid,
              new_values={"total": body.total, "items": len(body.items_json)})
    db.commit()
    return success_response("Sale suspended", {"id": sid})


@router.get("/pos/suspended")
def list_suspended(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,register_id,cashier_id,subtotal,total,suspended_at,notes "
                           "FROM dbp_retail_suspended_sales WHERE tenant_id=:t AND status='suspended' "
                           "ORDER BY suspended_at DESC"), {"t": t}).fetchall()
    data = [{"id": r[0], "register_id": r[1], "cashier_id": r[2],
             "subtotal": float(r[3] or 0), "total": float(r[4] or 0),
             "suspended_at": str(r[5]), "notes": r[6]} for r in rows]
    return list_response(data, len(data))


@router.post("/pos/suspended/{sus_id}/recall")
def recall_suspended(sus_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,items_json,subtotal,tax_amount,total,register_id,cashier_id,customer_id "
                          "FROM dbp_retail_suspended_sales WHERE id=:id AND tenant_id=:t"),
                     {"id": sus_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Suspended sale not found")
    db.execute(text("UPDATE dbp_retail_suspended_sales SET status='recalled' "
                    "WHERE id=:id AND tenant_id=:t"), {"id": sus_id, "t": t})
    audit_log(db, t, user["id"], "recall", "suspended_sale", sus_id)
    db.commit()
    return success_response("Sale recalled", {
        "items_json": row[1], "subtotal": float(row[2] or 0),
        "tax_amount": float(row[3] or 0), "total": float(row[4] or 0),
        "register_id": row[5], "cashier_id": row[6], "customer_id": row[7],
    })


# ═══════════════════════════════════════════════════
# CASH MANAGEMENT
# ═══════════════════════════════════════════════════

class CashSessionOpen(BaseModel):
    register_id: str
    cashier_id: str
    opening_amount: float = Field(ge=0)

@router.post("/cash/sessions/open")
def open_cash_session(body: CashSessionOpen, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_retail_cash_sessions "
                               "WHERE tenant_id=:t AND register_id=:r AND status='open'"),
                          {"t": t, "r": body.register_id}).fetchone()
    if existing:
        raise HTTPException(400, detail="Session already open for this register")

    sid = uid()
    sess_num = f"CS-{now().strftime('%Y%m%d')}-{sid[:6].upper()}"
    db.execute(text("INSERT INTO dbp_retail_cash_sessions "
                    "(id,tenant_id,session_number,register_id,cashier_id,opening_amount,status) "
                    "VALUES (:id,:t,:sn,:r,:ca,:oa,'open')"),
               {"id": sid, "t": t, "sn": sess_num, "r": body.register_id,
                "ca": body.cashier_id, "oa": body.opening_amount})
    db.execute(text("INSERT INTO dbp_retail_cash_movements "
                    "(id,tenant_id,session_id,movement_type,amount,reference,created_by) "
                    "VALUES (:id,:t,:si,'opening',:a,'Opening balance',:cb)"),
               {"id": uid(), "t": t, "si": sid, "a": body.opening_amount, "cb": user.get("email", "")})
    audit_log(db, t, user["id"], "open", "cash_session", sid,
              new_values={"opening": body.opening_amount})
    db.commit()
    return success_response("Session opened", {"id": sid, "session_number": sess_num})


class CashMovement(BaseModel):
    session_id: str
    movement_type: str
    amount: float
    reference: str | None = None
    notes: str | None = None

@router.post("/cash/movements")
def create_cash_movement(body: CashMovement, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_types = ["sale", "return", "withdrawal", "deposit"]
    if body.movement_type not in valid_types:
        raise HTTPException(400, detail=f"Invalid type: {body.movement_type}. Use: {valid_types}")
    if body.amount <= 0:
        raise HTTPException(400, detail=f"Amount must be positive: {body.amount}")

    sess = db.execute(text("SELECT id FROM dbp_retail_cash_sessions "
                           "WHERE id=:id AND tenant_id=:t AND status='open'"),
                      {"id": body.session_id, "t": t}).fetchone()
    if not sess:
        raise HTTPException(404, detail="Open session not found")

    mid = uid()
    db.execute(text("INSERT INTO dbp_retail_cash_movements "
                    "(id,tenant_id,session_id,movement_type,amount,reference,notes,created_by) "
                    "VALUES (:id,:t,:si,:mt,:a,:r,:n,:cb)"),
               {"id": mid, "t": t, "si": body.session_id, "mt": body.movement_type,
                "a": body.amount, "r": body.reference, "n": body.notes,
                "cb": user.get("email", "")})
    audit_log(db, t, user["id"], "create", "cash_movement", mid,
              new_values={"type": body.movement_type, "amount": body.amount})
    db.commit()
    return success_response("Movement recorded", {"id": mid})


@router.post("/cash/sessions/{sess_id}/close")
def close_cash_session(sess_id: str, closing_amount: float | None=None,
                       user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sess = db.execute(text("SELECT id,opening_amount FROM dbp_retail_cash_sessions "
                           "WHERE id=:id AND tenant_id=:t AND status='open'"),
                      {"id": sess_id, "t": t}).fetchone()
    if not sess:
        raise HTTPException(404, detail="Open session not found")

    opening = float(sess[1] or 0)
    movements = db.execute(text("SELECT movement_type,amount FROM dbp_retail_cash_movements "
                                "WHERE session_id=:si AND tenant_id=:t"),
                           {"si": sess_id, "t": t}).fetchall()
    cash_in = sum(float(m[1]) for m in movements if m[0] in ("sale", "deposit"))
    cash_out = sum(float(m[1]) for m in movements if m[0] in ("return", "withdrawal"))
    expected = opening + cash_in - cash_out
    variance = closing_amount - expected

    db.execute(text("UPDATE dbp_retail_cash_sessions "
                    "SET closed_at=NOW(), closing_amount=:ca, expected_amount=:ea, variance=:v, status='closed' "
                    "WHERE id=:id AND tenant_id=:t"),
               {"ca": closing_amount, "ea": expected, "v": variance, "id": sess_id, "t": t})
    db.execute(text("INSERT INTO dbp_retail_cash_movements "
                    "(id,tenant_id,session_id,movement_type,amount,reference,created_by) "
                    "VALUES (:id,:t,:si,'closing',:a,'Closing',:cb)"),
               {"id": uid(), "t": t, "si": sess_id, "a": closing_amount, "cb": user.get("email", "")})
    audit_log(db, t, user["id"], "close", "cash_session", sess_id,
              new_values={"expected": expected, "actual": closing_amount, "variance": variance})
    db.commit()
    return success_response("Session closed", {
        "opening": opening, "cash_in": cash_in, "cash_out": cash_out,
        "expected": expected, "actual": closing_amount, "variance": variance,
    })


@router.get("/cash/sessions")
def list_cash_sessions(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,session_number,register_id,cashier_id,"
                           "opening_amount,closing_amount,expected_amount,variance,"
                           "opened_at,closed_at,status "
                           "FROM dbp_retail_cash_sessions WHERE tenant_id=:t "
                           "ORDER BY opened_at DESC LIMIT 50"), {"t": t}).fetchall()
    data = [{"id": r[0], "session_number": r[1], "register_id": r[2], "cashier_id": r[3],
             "opening": float(r[4] or 0), "closing": float(r[5] or 0) if r[5] else None,
             "expected": float(r[6] or 0) if r[6] else None,
             "variance": float(r[7] or 0) if r[7] else None,
             "opened_at": str(r[8]), "closed_at": str(r[9]) if r[9] else None,
             "status": r[10]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# LOYALTY
# ═══════════════════════════════════════════════════

@router.get("/loyalty/tiers")
def list_loyalty_tiers(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,min_points,discount_pct,points_multiplier "
                           "FROM dbp_retail_loyalty_tiers WHERE tenant_id=:t ORDER BY min_points"),
                      {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "min_points": r[2],
             "discount_pct": float(r[3] or 0), "points_multiplier": float(r[4] or 1)} for r in rows]
    return list_response(data, len(data))


class LoyaltyAccountCreate(BaseModel):
    customer_id: str

@router.post("/loyalty/accounts")
def create_loyalty_account(body: LoyaltyAccountCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_retail_loyalty_accounts "
                               "WHERE tenant_id=:t AND customer_id=:cu"),
                          {"t": t, "cu": body.customer_id}).fetchone()
    if existing:
        raise HTTPException(400, detail="Loyalty account already exists")

    bronze = db.execute(text("SELECT id FROM dbp_retail_loyalty_tiers "
                             "WHERE tenant_id=:t AND name='Bronze'"), {"t": t}).fetchone()
    aid = uid()
    db.execute(text("INSERT INTO dbp_retail_loyalty_accounts "
                    "(id,tenant_id,customer_id,tier_id,total_points,available_points) "
                    "VALUES (:id,:t,:cu,:ti,0,0)"),
               {"id": aid, "t": t, "cu": body.customer_id, "ti": bronze[0] if bronze else None})
    db.commit()
    return success_response("Loyalty account created", {"id": aid})


@router.get("/loyalty/accounts")
def list_loyalty_accounts(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT la.id,la.customer_id,c.name,lt.name,la.total_points,"
                           "la.redeemed_points,la.available_points,la.lifetime_spend "
                           "FROM dbp_retail_loyalty_accounts la "
                           "LEFT JOIN dbp_commerce_customers c ON la.customer_id=c.id "
                           "LEFT JOIN dbp_retail_loyalty_tiers lt ON la.tier_id=lt.id "
                           "WHERE la.tenant_id=:t ORDER BY la.created_at"), {"t": t}).fetchall()
    data = [{"id": r[0], "customer_id": r[1], "customer_name": r[2], "tier": r[3],
             "total_points": r[4], "redeemed": r[5], "available": r[6],
             "lifetime_spend": float(r[7] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/loyalty/accounts/{acct_id}")
def get_loyalty_account(acct_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT la.id,la.customer_id,c.name,lt.name,la.total_points,"
                          "la.redeemed_points,la.available_points,la.lifetime_spend "
                          "FROM dbp_retail_loyalty_accounts la "
                          "LEFT JOIN dbp_commerce_customers c ON la.customer_id=c.id "
                          "LEFT JOIN dbp_retail_loyalty_tiers lt ON la.tier_id=lt.id "
                          "WHERE la.id=:id AND la.tenant_id=:t"),
                     {"id": acct_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Loyalty account not found")
    return success_response("Account found", {
        "id": row[0], "customer_id": row[1], "customer_name": row[2], "tier": row[3],
        "total_points": row[4], "redeemed": row[5], "available": row[6],
        "lifetime_spend": float(row[7] or 0)})


@router.get("/loyalty/transactions/{account_id}")
def list_loyalty_transactions(account_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,transaction_type,points,description,created_at "
                           "FROM dbp_retail_loyalty_transactions "
                           "WHERE account_id=:aid AND tenant_id=:t ORDER BY created_at DESC LIMIT 50"),
                      {"aid": account_id, "t": t}).fetchall()
    data = [{"id": r[0], "type": r[1], "points": r[2], "description": r[3],
             "created_at": str(r[4])} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# PROMOTIONS
# ═══════════════════════════════════════════════════

class PromoCreate(BaseModel):
    name: str
    name_ar: str | None = None
    promo_type: str
    discount_value: float = 0
    buy_qty: int | None = None
    get_qty: int | None = None
    min_purchase: float = 0
    start_date: str
    end_date: str

@router.post("/promotions")
def create_promotion(body: PromoCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    pid = uid()
    db.execute(text("INSERT INTO dbp_retail_promotions "
                    "(id,tenant_id,name,name_ar,promo_type,discount_value,buy_qty,get_qty,"
                    "min_purchase,start_date,end_date,status) "
                    "VALUES (:id,:t,:n,:na,:pt,:dv,:bq,:gq,:mp,:sd,:ed,'active')"),
               {"id": pid, "t": t, "n": body.name, "na": body.name_ar,
                "pt": body.promo_type, "dv": body.discount_value,
                "bq": body.buy_qty, "gq": body.get_qty,
                "mp": body.min_purchase, "sd": body.start_date, "ed": body.end_date})
    audit_log(db, t, user["id"], "create", "promotion", pid, new_values={"name": body.name})
    db.commit()
    return success_response("Promotion created", {"id": pid})


@router.get("/promotions")
def list_promotions(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,name_ar,promo_type,discount_value,start_date,end_date,status "
                           "FROM dbp_retail_promotions WHERE tenant_id=:t ORDER BY created_at"), {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "name_ar": r[2], "type": r[3],
             "discount": float(r[4] or 0), "start": str(r[5]), "end": str(r[6]),
             "status": r[7]} for r in rows]
    return list_response(data, len(data))


@router.get("/promotions/{promo_id}")
def get_promotion(promo_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,name,name_ar,promo_type,discount_value,buy_qty,get_qty,"
                          "min_purchase,start_date,end_date,status "
                          "FROM dbp_retail_promotions WHERE id=:id AND tenant_id=:t"),
                     {"id": promo_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Promotion not found")
    return success_response("Promotion found", {
        "id": row[0], "name": row[1], "name_ar": row[2], "type": row[3],
        "discount": float(row[4] or 0), "buy_qty": row[5], "get_qty": row[6],
        "min_purchase": float(row[7] or 0), "start": str(row[8]), "end": str(row[9]),
        "status": row[10]})


# ═══════════════════════════════════════════════════
# ANALYTICS & DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/dashboard")
def retail_dashboard(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]

    today = db.execute(text("SELECT COUNT(*),COALESCE(SUM(total),0),COALESCE(SUM(tax_amount),0) "
                            "FROM dbp_retail_pos_sales WHERE tenant_id=:t AND status='completed' "
                            "AND DATE(sale_date)=CURRENT_DATE"), {"t": t}).fetchone()

    month = db.execute(text("SELECT COUNT(*),COALESCE(SUM(total),0),COALESCE(SUM(discount_amount),0) "
                            "FROM dbp_retail_pos_sales WHERE tenant_id=:t AND status='completed' "
                            "AND sale_date>=date_trunc('month',NOW())"), {"t": t}).fetchone()

    returns_m = db.execute(text("SELECT COUNT(*),COALESCE(SUM(ABS(total)),0) "
                                "FROM dbp_retail_pos_sales WHERE tenant_id=:t AND is_return=true "
                                "AND sale_date>=date_trunc('month',NOW())"), {"t": t}).fetchone()

    top_items = db.execute(text("SELECT pl.description,SUM(pl.qty),SUM(pl.line_total) "
                                "FROM dbp_retail_pos_lines pl "
                                "JOIN dbp_retail_pos_sales ps ON pl.sale_id=ps.id "
                                "WHERE ps.tenant_id=:t AND ps.status='completed' "
                                "AND ps.sale_date>=date_trunc('month',NOW()) "
                                "GROUP BY pl.description ORDER BY SUM(pl.line_total) DESC LIMIT 5"),
                           {"t": t}).fetchall()

    active_cashiers = db.execute(text("SELECT COUNT(*) FROM dbp_retail_cashiers "
                                      "WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()

    open_sessions = db.execute(text("SELECT COUNT(*) FROM dbp_retail_cash_sessions "
                                    "WHERE tenant_id=:t AND status='open'"), {"t": t}).fetchone()

    loyalty_members = db.execute(text("SELECT COUNT(*) FROM dbp_retail_loyalty_accounts "
                                      "WHERE tenant_id=:t"), {"t": t}).fetchone()

    active_promos = db.execute(text("SELECT COUNT(*) FROM dbp_retail_promotions "
                                    "WHERE tenant_id=:t AND status='active' "
                                    "AND start_date<=CURRENT_DATE AND end_date>=CURRENT_DATE"),
                               {"t": t}).fetchone()

    return success_response("Retail dashboard", {
        "today": {"transactions": today[0], "revenue": float(today[1] or 0), "tax": float(today[2] or 0)},
        "month": {"transactions": month[0], "revenue": float(month[1] or 0), "discounts": float(month[2] or 0)},
        "returns_month": {"count": returns_m[0], "amount": float(returns_m[1] or 0)},
        "top_items": [{"name": r[0], "qty": float(r[1] or 0), "revenue": float(r[2] or 0)} for r in top_items],
        "active_cashiers": active_cashiers[0],
        "open_sessions": open_sessions[0],
        "loyalty_members": loyalty_members[0],
        "active_promotions": active_promos[0],
    })


@router.get("/analytics/top-products")
def top_products(days: int | None=None,
                 user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT pl.description,SUM(pl.qty) as total_qty,"
                           "SUM(pl.line_total) as total_revenue,AVG(pl.unit_price) as avg_price "
                           "FROM dbp_retail_pos_lines pl "
                           "JOIN dbp_retail_pos_sales ps ON pl.sale_id=ps.id "
                           "WHERE ps.tenant_id=:t AND ps.status='completed' "
                           "AND ps.sale_date>=NOW()-INTERVAL ':d days' "
                           "GROUP BY pl.description ORDER BY total_revenue DESC LIMIT 20"),
                      {"t": t, "d": days}).fetchall()
    data = [{"name": r[0], "qty_sold": float(r[1] or 0), "revenue": float(r[2] or 0),
             "avg_price": float(r[3] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/analytics/cashier-performance")
def cashier_performance(days: int | None=None,
                        user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT c.name,COUNT(ps.id),SUM(ps.total),AVG(ps.total) "
                           "FROM dbp_retail_pos_sales ps "
                           "JOIN dbp_retail_cashiers c ON ps.cashier_id=c.id "
                           "WHERE ps.tenant_id=:t AND ps.status='completed' "
                           "AND ps.sale_date>=NOW()-INTERVAL ':d days' "
                           "GROUP BY c.name ORDER BY SUM(ps.total) DESC"),
                      {"t": t, "d": days}).fetchall()
    data = [{"cashier": r[0], "transactions": r[1], "total_sales": float(r[2] or 0),
             "avg_sale": float(r[3] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/analytics/basket-size")
def basket_size_analysis(days: int | None=None,
                         user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT DATE(ps.sale_date),COUNT(DISTINCT ps.id),"
                           "SUM(pl.qty)/COUNT(DISTINCT ps.id),SUM(ps.total)/COUNT(DISTINCT ps.id) "
                           "FROM dbp_retail_pos_sales ps "
                           "JOIN dbp_retail_pos_lines pl ON ps.id=pl.sale_id "
                           "WHERE ps.tenant_id=:t AND ps.status='completed' "
                           "AND ps.sale_date>=NOW()-INTERVAL ':d days' "
                           "GROUP BY DATE(ps.sale_date) ORDER BY DATE(ps.sale_date)"),
                      {"t": t, "d": days}).fetchall()
    data = [{"date": str(r[0]), "transactions": r[1],
             "avg_items": float(r[2] or 0), "avg_basket": float(r[3] or 0)} for r in rows]
    return list_response(data, len(data))
