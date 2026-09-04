"""
P70.4 Trading ERP Professional — API
=====================================
Uses core/industry_security.py for all hardening (H1-H7).
Commerce operations delegated to core/commerce_engine.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.commerce_engine import (
    create_customer as _ce_create_customer,
)
from core.commerce_engine import (
    create_item as _ce_create_item,
)
from core.commerce_engine import (
    create_price_list as _ce_create_price_list,
)
from core.commerce_engine import (
    create_supplier as _ce_create_supplier,
)
from core.commerce_engine import (
    create_warehouse as _ce_create_warehouse,
)
from core.commerce_engine import (
    get_customer as _ce_get_customer,
)
from core.commerce_engine import (
    get_item as _ce_get_item,
)
from core.commerce_engine import (
    get_supplier as _ce_get_supplier,
)
from core.commerce_engine import (
    list_customers as _ce_list_customers,
)
from core.commerce_engine import (
    list_items as _ce_list_items,
)
from core.commerce_engine import (
    list_price_lists as _ce_list_price_lists,
)
from core.commerce_engine import (
    list_stock as _ce_list_stock,
)
from core.commerce_engine import (
    list_suppliers as _ce_list_suppliers,
)
from core.commerce_engine import (
    list_warehouses as _ce_list_warehouses,
)
from core.commerce_engine import (
    update_customer as _ce_update_customer,
)
from core.commerce_engine import (
    update_item as _ce_update_item,
)
from core.commerce_engine import (
    update_supplier as _ce_update_supplier,
)
from core.industry_security import (
    atomic_stock_issue,
    atomic_stock_receive,
    audit_log,
    check_permission,
    get_company_id,
    list_response,
    now,
    post_journal,
    success_response,
    uid,
)
from database import get_db

router = APIRouter(prefix="/trading", tags=["Trading"])


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _get_item(db, tenant_id, item_id):
    return _ce_get_item(db, tenant_id, item_id)


def _get_stock(db, tenant_id, item_id, warehouse_id="default"):
    return db.execute(text("SELECT id, on_hand, reserved, in_transit, unit_cost "
                           "FROM dbp_commerce_stock WHERE tenant_id=:t AND item_id=:iid "
                           "AND warehouse_id=:w FOR UPDATE"),
                      {"t": tenant_id, "iid": item_id, "w": warehouse_id}).fetchone()


def _recalc_stock(db, tenant_id, item_id, warehouse_id="default"):
    """Recalculate weighted average cost after GRN."""
    stock = db.execute(text("SELECT id, on_hand, unit_cost FROM dbp_commerce_stock "
                            "WHERE tenant_id=:t AND item_id=:iid AND warehouse_id=:w"),
                       {"t": tenant_id, "iid": item_id, "w": warehouse_id}).fetchone()
    if stock and float(stock[1]) > 0:
        db.execute(text("UPDATE dbp_commerce_items SET cost_price=:cp WHERE id=:iid"),
                   {"cp": float(stock[2]), "iid": item_id})


def _get_customer_credit(db, tenant_id, customer_id):
    cust = _ce_get_customer(db, tenant_id, customer_id)
    return cust.get("credit_limit", 0), cust.get("current_balance", 0)


def _check_credit_limit(db, tenant_id, customer_id, order_amount):
    limit, balance = _get_customer_credit(db, tenant_id, customer_id)
    if limit > 0 and (balance + order_amount) > limit:
        raise HTTPException(400, detail=(
            f"Credit limit exceeded: Limit={limit}, Balance={balance}, "
            f"New Order={order_amount}, Available={limit - balance}"))


from sqlalchemy import text

# ═══════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    date.today()

    # Sales this month
    sales = db.execute(text(
        "SELECT COUNT(*), COALESCE(SUM(total),0) FROM dbp_trading_sales_orders "
        "WHERE tenant_id=:t AND status != 'cancelled' "
        "AND EXTRACT(MONTH FROM order_date)=EXTRACT(MONTH FROM CURRENT_DATE) "
        "AND EXTRACT(YEAR FROM order_date)=EXTRACT(YEAR FROM CURRENT_DATE)"),
        {"t": t}).fetchone()

    # Purchases this month
    purchases = db.execute(text(
        "SELECT COUNT(*), COALESCE(SUM(total),0) FROM dbp_trading_purchase_orders "
        "WHERE tenant_id=:t AND status != 'cancelled' "
        "AND EXTRACT(MONTH FROM order_date)=EXTRACT(MONTH FROM CURRENT_DATE) "
        "AND EXTRACT(YEAR FROM order_date)=EXTRACT(YEAR FROM CURRENT_DATE)"),
        {"t": t}).fetchone()

    # Receivables (unpaid invoices)
    receivables = db.execute(text(
        "SELECT COUNT(*), COALESCE(SUM(balance),0) FROM dbp_trading_sales_invoices "
        "WHERE tenant_id=:t AND balance > 0"), {"t": t}).fetchone()

    # Payables (unpaid purchase invoices)
    payables = db.execute(text(
        "SELECT COUNT(*), COALESCE(SUM(balance),0) FROM dbp_trading_purchase_invoices "
        "WHERE tenant_id=:t AND balance > 0"), {"t": t}).fetchone()

    # Stock value (Fixed H15: consolidated to dbp_commerce_stock)
    stock_val = db.execute(text(
        "SELECT COUNT(*), COALESCE(SUM(on_hand * unit_cost),0) FROM dbp_commerce_stock "
        "WHERE tenant_id=:t AND on_hand > 0"), {"t": t}).fetchone()

    # Low stock alerts
    low_stock = db.execute(text(
        "SELECT COUNT(*) FROM dbp_trading_items i "
        "JOIN dbp_commerce_stock s ON s.item_id = i.id "
        "WHERE i.tenant_id=:t AND s.on_hand <= i.reorder_point AND i.reorder_point > 0"),
        {"t": t}).fetchone()

    # Items count
    items_count = db.execute(text("SELECT COUNT(*) FROM dbp_trading_items WHERE tenant_id=:t"),
                             {"t": t}).fetchone()

    # Customers count
    cust_count = db.execute(text("SELECT COUNT(*) FROM dbp_trading_customers WHERE tenant_id=:t"),
                            {"t": t}).fetchone()

    return success_response("Dashboard", {
        "sales": {"count": sales[0], "total": float(sales[1])},
        "purchases": {"count": purchases[0], "total": float(purchases[1])},
        "receivables": {"count": receivables[0], "total": float(receivables[1])},
        "payables": {"count": payables[0], "total": float(payables[1])},
        "stock": {"items": stock_val[0], "value": float(stock_val[1])},
        "low_stock_alerts": low_stock[0],
        "total_items": items_count[0],
        "total_customers": cust_count[0],
    })


# ═══════════════════════════════════════════════════
# ITEMS
# ═══════════════════════════════════════════════════

class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = None
    category: str | None = None
    unit: str = "piece"
    cost_price: float = Field(ge=0, default=0)
    selling_price: float = Field(ge=0, default=0)
    min_stock: float = Field(ge=0, default=0)
    reorder_point: float = Field(ge=0, default=0)
    has_batch: bool = False
    has_serial: bool = False
    has_expiry: bool = False
    barcode: str | None = None
    description: str | None = None
    description_ar: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    category: str | None = None
    unit: str | None = None
    cost_price: float | None = None
    selling_price: float | None = None
    min_stock: float | None = None
    reorder_point: float | None = None
    has_batch: bool | None = None
    has_serial: bool | None = None
    has_expiry: bool | None = None
    barcode: str | None = None
    description: str | None = None
    status: str | None = None


@router.get("/items")
def list_items(user: dict | None=None, db=Depends(get_db),
               page: int = 1, page_size: int = 50,
               search: str | None = None, category: str | None = None):
    check_permission(user, "read")
    t = user["tenant_id"]
    result = _ce_list_items(db, t, page, page_size, search or "", category or "")
    items = result["data"]
    for item in items:
        stock = db.execute(text("SELECT SUM(on_hand), SUM(reserved) FROM dbp_commerce_stock "
                                "WHERE item_id=:iid AND tenant_id=:t"),
                           {"iid": item["id"], "t": t}).fetchone()
        item["on_hand"] = float(stock[0] or 0) if stock else 0
        item["reserved"] = float(stock[1] or 0) if stock else 0
    return list_response(items, result["total"], page, page_size)


@router.post("/items")
def create_item(body: ItemCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    code = f"ITM-{uid()[:8].upper()}"
    data = body.model_dump()
    data["item_code"] = code
    result = _ce_create_item(db, t, data, user_id=user["id"])
    return success_response("Item created", {"id": result["id"], "item_code": result["item_code"]})


@router.put("/items/{item_id}")
def update_item(item_id: str, body: ItemUpdate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return success_response("No changes")
    _ce_update_item(db, t, item_id, updates, user_id=user["id"])
    return success_response("Item updated")


# ═══════════════════════════════════════════════════
# WAREHOUSES
# ═══════════════════════════════════════════════════

class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = None
    address: str | None = None
    manager: str | None = None


@router.get("/warehouses")
def list_warehouses(user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    whs = _ce_list_warehouses(db, t)
    return list_response(whs, len(whs))


@router.post("/warehouses")
def create_warehouse(body: WarehouseCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    code = f"WH-{uid()[:6].upper()}"
    data = body.model_dump()
    data["code"] = code
    result = _ce_create_warehouse(db, t, data, user_id=user["id"])
    return success_response("Warehouse created", {"id": result["id"], "code": result["code"]})


# ═══════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    credit_limit: float = 0
    territory: str | None = None
    salesman: str | None = None
    payment_terms: str = "net30"


class CustomerUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    credit_limit: float | None = None
    territory: str | None = None
    salesman: str | None = None
    payment_terms: str | None = None
    status: str | None = None


@router.get("/customers")
def list_customers(user: dict | None=None, db=Depends(get_db),
                   page: int = 1, page_size: int = 50, search: str | None = None):
    check_permission(user, "read")
    t = user["tenant_id"]
    result = _ce_list_customers(db, t, page, page_size, search or "")
    return list_response(result["data"], result["total"], page, page_size)


@router.post("/customers")
def create_customer(body: CustomerCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    code = f"CUST-{uid()[:8].upper()}"
    data = body.model_dump()
    data["customer_code"] = code
    result = _ce_create_customer(db, t, data, user_id=user["id"])
    return success_response("Customer created", {"id": result["id"], "customer_code": result["customer_code"]})


@router.put("/customers/{customer_id}")
def update_customer(customer_id: str, body: CustomerUpdate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return success_response("No changes")
    _ce_update_customer(db, t, customer_id, updates, user_id=user["id"])
    return success_response("Customer updated")


# ═══════════════════════════════════════════════════
# SUPPLIERS
# ═══════════════════════════════════════════════════

class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_terms: str = "net30"
    lead_time_days: int = 7


class SupplierUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_terms: str | None = None
    lead_time_days: int | None = None
    status: str | None = None


@router.get("/suppliers")
def list_suppliers(user: dict | None=None, db=Depends(get_db),
                   page: int = 1, page_size: int = 50, search: str | None = None):
    check_permission(user, "read")
    t = user["tenant_id"]
    result = _ce_list_suppliers(db, t, page, page_size, search or "")
    return list_response(result["data"], result["total"], page, page_size)


@router.post("/suppliers")
def create_supplier(body: SupplierCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    code = f"SUP-{uid()[:8].upper()}"
    data = body.model_dump()
    data["supplier_code"] = code
    result = _ce_create_supplier(db, t, data, user_id=user["id"])
    return success_response("Supplier created", {"id": result["id"], "supplier_code": result["supplier_code"]})


@router.put("/suppliers/{supplier_id}")
def update_supplier(supplier_id: str, body: SupplierUpdate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return success_response("No changes")
    _ce_update_supplier(db, t, supplier_id, updates, user_id=user["id"])
    return success_response("Supplier updated")


# ═══════════════════════════════════════════════════
# SALES: QUOTATION → SO → DELIVERY → INVOICE → PAYMENT
# ═══════════════════════════════════════════════════

class QuotationLine(BaseModel):
    item_id: str
    description: str | None = None
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount_pct: float = 0


class QuotationCreate(BaseModel):
    customer_id: str
    valid_days: int = 30
    tax_rate: float = 0
    discount_rate: float = 0
    notes: str | None = None
    lines: list[QuotationLine]


@router.post("/quotations")
def create_quotation(body: QuotationCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    qid = uid()
    qnum = f"QT-{now().strftime('%Y%m%d')}-{qid[:6].upper()}"
    subtotal = 0
    for l in body.lines:
        line_total = l.qty * l.unit_price * (1 - l.discount_pct / 100)
        subtotal += line_total
    tax_amt = subtotal * body.tax_rate / 100
    disc_amt = subtotal * body.discount_rate / 100
    total = subtotal + tax_amt - disc_amt

    db.execute(text("INSERT INTO dbp_trading_quotations "
                    "(id,tenant_id,quote_number,customer_id,valid_until,subtotal,tax_rate,tax_amount,"
                    "discount_rate,discount_amount,total,notes,status,created_by) "
                    "VALUES (:id,:t,:qn,:cid,:vu,:sub,:tr,:ta,:dr,:da,:tot,:notes,'draft',:cb)"),
               {"id": qid, "t": t, "qn": qnum, "cid": body.customer_id,
                "vu": date.today() + timedelta(days=body.valid_days),
                "sub": subtotal, "tr": body.tax_rate, "ta": tax_amt,
                "dr": body.discount_rate, "da": disc_amt, "tot": total,
                "notes": body.notes, "cb": user.get("email", "")})
    for l in body.lines:
        lid = uid()
        lt = l.qty * l.unit_price * (1 - l.discount_pct / 100)
        db.execute(text("INSERT INTO dbp_trading_quotation_lines "
                        "(id,tenant_id,quotation_id,item_id,description,qty,unit_price,discount_pct,line_total) "
                        "VALUES (:id,:t,:qid,:iid,:desc,:qty,:up,:dp,:lt)"),
                   {"id": lid, "t": t, "qid": qid, "iid": l.item_id, "desc": l.description,
                    "qty": l.qty, "up": l.unit_price, "dp": l.discount_pct, "lt": lt})
    audit_log(db, t, user["id"], "create", "quotation", qid, new_values={"total": total})
    db.commit()
    return success_response("Quotation created", {"id": qid, "quote_number": qnum, "total": total})


class SOCreate(BaseModel):
    customer_id: str
    quotation_id: str | None = None
    delivery_date: str | None = None
    tax_rate: float = 0
    discount_rate: float = 0
    notes: str | None = None
    lines: list[QuotationLine]


@router.post("/sales-orders")
def create_sales_order(body: SOCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    so_id = uid()
    so_num = f"SO-{now().strftime('%Y%m%d')}-{so_id[:6].upper()}"

    subtotal = 0
    lines_data = []
    for l in body.lines:
        line_total = l.qty * l.unit_price * (1 - l.discount_pct / 100)
        item = _get_item(db, t, l.item_id)
        subtotal += line_total
        lines_data.append((l, line_total, float(item.get("cost_price", 0) or 0)))

    tax_amt = subtotal * body.tax_rate / 100
    disc_amt = subtotal * body.discount_rate / 100
    total = subtotal + tax_amt - disc_amt

    # H2: Credit check
    _check_credit_limit(db, t, body.customer_id, total)

    db.execute(text("INSERT INTO dbp_trading_sales_orders "
                    "(id,tenant_id,so_number,customer_id,quotation_id,delivery_date,subtotal,"
                    "tax_rate,tax_amount,discount_rate,discount_amount,total,notes,status,created_by) "
                    "VALUES (:id,:t,:sn,:cid,:qid,:dd,:sub,:tr,:ta,:dr,:da,:tot,:notes,'draft',:cb)"),
               {"id": so_id, "t": t, "sn": so_num, "cid": body.customer_id,
                "qid": body.quotation_id, "dd": body.delivery_date,
                "sub": subtotal, "tr": body.tax_rate, "ta": tax_amt,
                "dr": body.discount_rate, "da": disc_amt, "tot": total,
                "notes": body.notes, "cb": user.get("email", "")})
    for l, lt, cp in lines_data:
        lid = uid()
        db.execute(text("INSERT INTO dbp_trading_sales_order_lines "
                        "(id,tenant_id,so_id,item_id,description,qty,unit_price,cost_price,discount_pct,line_total) "
                        "VALUES (:id,:t,:so,:iid,:desc,:qty,:up,:cp,:dp,:lt)"),
                   {"id": lid, "t": t, "so": so_id, "iid": l.item_id, "desc": l.description,
                    "qty": l.qty, "up": l.unit_price, "cp": cp, "dp": l.discount_pct, "lt": lt})

    # Update quotation status if linked
    if body.quotation_id:
        db.execute(text("UPDATE dbp_trading_quotations SET status='accepted' WHERE id=:qid"),
                   {"qid": body.quotation_id})

    audit_log(db, t, user["id"], "create", "sales_order", so_id, new_values={"total": total})
    db.commit()
    return success_response("Sales Order created", {"id": so_id, "so_number": so_num, "total": total})


class DeliveryLine(BaseModel):
    item_id: str
    qty: float = Field(gt=0)
    warehouse_id: str | None = "default"


class DeliveryCreate(BaseModel):
    so_id: str
    driver_name: str | None = None
    vehicle_number: str | None = None
    notes: str | None = None
    lines: list[DeliveryLine]


@router.post("/deliveries")
def create_delivery(body: DeliveryCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    so = db.execute(text("SELECT id, customer_id, status FROM dbp_trading_sales_orders "
                         "WHERE id=:id AND tenant_id=:t"),
                    {"id": body.so_id, "t": t}).fetchone()
    if not so:
        raise HTTPException(404, detail="Sales Order not found")

    dn_id = uid()
    dn_num = f"DN-{now().strftime('%Y%m%d')}-{dn_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_delivery_notes "
                    "(id,tenant_id,dn_number,so_id,customer_id,driver_name,vehicle_number,notes,status,created_by) "
                    "VALUES (:id,:t,:dn,:so,:cid,:dr,:vn,:notes,'pending',:cb)"),
               {"id": dn_id, "t": t, "dn": dn_num, "so": body.so_id,
                "cid": so[1], "dr": body.driver_name, "vn": body.vehicle_number,
                "notes": body.notes, "cb": user.get("email", "")})

    for l in body.lines:
        lid = uid()
        db.execute(text("INSERT INTO dbp_trading_delivery_lines "
                        "(id,tenant_id,dn_id,item_id,qty) VALUES (:id,:t,:dn,:iid,:qty)"),
                   {"id": lid, "t": t, "dn": dn_id, "iid": l.item_id, "qty": l.qty})

        # H4: Atomic stock issue
        wh_id = l.warehouse_id or "default"
        _stock_id, unit_cost = atomic_stock_issue(db, t, l.item_id, l.qty, wh_id,
                                                   stock_table="dbp_commerce_stock", item_column="item_id")

        # H7: Journal: Dr COGS / Cr Inventory
        company_id = get_company_id(db, t)
        post_journal(db, t, company_id, "delivery",
                                  f"DN {dn_num} — COGS",
                                  [{"account_code": "5100", "description": "COGS",
                                    "debit": l.qty * unit_cost},
                                   {"account_code": "1300", "description": "Inventory",
                                    "credit": l.qty * unit_cost}])
        # Update SO delivered_qty (with tenant isolation)
        db.execute(text("UPDATE dbp_trading_sales_order_lines SET delivered_qty=delivered_qty+:q "
                        "WHERE so_id=:so AND item_id=:iid AND tenant_id=:t"),
                   {"q": l.qty, "so": body.so_id, "iid": l.item_id, "t": t})

    # Update SO delivery status (with tenant isolation)
    db.execute(text("UPDATE dbp_trading_sales_orders SET delivery_status='delivered' WHERE id=:so AND tenant_id=:t"),
               {"so": body.so_id, "t": t})

    audit_log(db, t, user["id"], "create", "delivery", dn_id, new_values={"dn_number": dn_num})
    db.commit()
    return success_response("Delivery processed", {"id": dn_id, "dn_number": dn_num})


class SalesInvoiceCreate(BaseModel):
    so_id: str | None = None
    dn_id: str | None = None
    customer_id: str
    tax_rate: float = 0
    due_days: int = 30


@router.post("/sales-invoices")
def create_sales_invoice(body: SalesInvoiceCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    # Get amounts from SO lines
    if body.so_id:
        so_lines = db.execute(text(
            "SELECT SUM(line_total) FROM dbp_trading_sales_order_lines WHERE so_id=:so"),
            {"so": body.so_id}).fetchone()
        subtotal = float(so_lines[0] or 0)
    else:
        subtotal = 0

    tax_amt = subtotal * body.tax_rate / 100
    total = subtotal + tax_amt
    inv_id = uid()
    inv_num = f"INV-{now().strftime('%Y%m%d')}-{inv_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_sales_invoices "
                    "(id,tenant_id,invoice_number,so_id,dn_id,customer_id,due_date,"
                    "subtotal,tax_rate,tax_amount,total,balance,status,created_by) "
                    "VALUES (:id,:t,:inv,:so,:dn,:cid,:dd,:sub,:tr,:ta,:tot,:bal,'unpaid',:cb)"),
               {"id": inv_id, "t": t, "inv": inv_num, "so": body.so_id, "dn": body.dn_id,
                "cid": body.customer_id, "dd": date.today() + timedelta(days=body.due_days),
                "sub": subtotal, "tr": body.tax_rate, "ta": tax_amt, "tot": total,
                "bal": total, "cb": user.get("email", "")})

    # H7: Journal: Dr AR / Cr Revenue
    company_id = get_company_id(db, t)
    journal_id = post_journal(db, t, company_id, "sales_invoice",
                              f"Invoice {inv_num}",
                              [{"account_code": "1200", "description": "Accounts Receivable",
                                "debit": total},
                               {"account_code": "4100", "description": "Sales Revenue",
                                "credit": total}])

    db.execute(text("UPDATE dbp_trading_sales_invoices SET journal_entry_id=:je WHERE id=:id"),
               {"je": journal_id, "id": inv_id})

    # Update SO invoice status (with tenant isolation)
    if body.so_id:
        db.execute(text("UPDATE dbp_trading_sales_orders SET invoice_status='invoiced' WHERE id=:so AND tenant_id=:t"),
                   {"so": body.so_id, "t": t})

    # Update customer balance (with tenant isolation)
    db.execute(text("UPDATE dbp_trading_customers SET current_balance=current_balance+:bal WHERE id=:cid AND tenant_id=:t"),
               {"bal": total, "cid": body.customer_id, "t": t})

    audit_log(db, t, user["id"], "create", "sales_invoice", inv_id, new_values={"total": total})
    db.commit()
    return success_response("Invoice created", {"id": inv_id, "invoice_number": inv_num, "total": total})


class PaymentCreate(BaseModel):
    customer_id: str
    invoice_id: str | None = None
    amount: float = Field(gt=0)
    payment_method: str = "cash"
    reference: str | None = None


@router.post("/customer-payments")
def create_customer_payment(body: PaymentCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    pay_id = uid()
    pay_num = f"CP-{now().strftime('%Y%m%d')}-{pay_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_customer_payments "
                    "(id,tenant_id,payment_number,customer_id,invoice_id,amount,payment_method,reference,created_by) "
                    "VALUES (:id,:t,:pn,:cid,:iid,:amt,:pm,:ref,:cb)"),
               {"id": pay_id, "t": t, "pn": pay_num, "cid": body.customer_id,
                "iid": body.invoice_id, "amt": body.amount, "pm": body.payment_method,
                "ref": body.reference, "cb": user.get("email", "")})

    # Update invoice paid_amount and balance (with tenant isolation)
    if body.invoice_id:
        inv = db.execute(text("SELECT total, paid_amount FROM dbp_trading_sales_invoices "
                              "WHERE id=:id AND tenant_id=:t"),
                         {"id": body.invoice_id, "t": t}).fetchone()
        if inv:
            new_paid = float(inv[1] or 0) + body.amount
            new_bal = float(inv[0] or 0) - new_paid
            new_status = "paid" if new_bal <= 0 else "partial"
            db.execute(text("UPDATE dbp_trading_sales_invoices SET paid_amount=:pa, balance=:bal, status=:st "
                            "WHERE id=:id AND tenant_id=:t"),
                       {"pa": new_paid, "bal": max(new_bal, 0), "st": new_status,
                        "id": body.invoice_id, "t": t})

    # Update customer balance (with tenant isolation)
    db.execute(text("UPDATE dbp_trading_customers SET current_balance=current_balance-:amt "
                    "WHERE id=:cid AND tenant_id=:t"),
               {"amt": body.amount, "cid": body.customer_id, "t": t})

    # H7: Journal: Dr Cash / Cr AR
    company_id = get_company_id(db, t)
    journal_id = post_journal(db, t, company_id, "customer_payment",
                              f"Payment {pay_num}",
                              [{"account_code": "1100", "description": "Cash/Bank",
                                "debit": body.amount},
                               {"account_code": "1200", "description": "Accounts Receivable",
                                "credit": body.amount}])

    db.execute(text("UPDATE dbp_trading_customer_payments SET journal_entry_id=:je WHERE id=:id"),
               {"je": journal_id, "id": pay_id})

    audit_log(db, t, user["id"], "create", "customer_payment", pay_id,
              new_values={"amount": body.amount})
    db.commit()
    return success_response("Payment recorded", {"id": pay_id, "payment_number": pay_num})


# ═══════════════════════════════════════════════════
# PURCHASES: PR → RFQ → SQ → PO → GRN → INVOICE → PAYMENT
# ═══════════════════════════════════════════════════

class PRLine(BaseModel):
    item_id: str
    qty: float = Field(gt=0)
    estimated_price: float = 0
    notes: str | None = None


class PRCreate(BaseModel):
    notes: str | None = None
    lines: list[PRLine]


@router.post("/purchase-requests")
def create_purchase_request(body: PRCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    pr_id = uid()
    pr_num = f"PR-{now().strftime('%Y%m%d')}-{pr_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_purchase_requests "
                    "(id,tenant_id,pr_number,requested_by,notes,status) "
                    "VALUES (:id,:t,:pn,:rb,:notes,'draft')"),
               {"id": pr_id, "t": t, "pn": pr_num, "rb": user.get("email", ""), "notes": body.notes})
    for l in body.lines:
        lid = uid()
        db.execute(text("INSERT INTO dbp_trading_purchase_request_lines "
                        "(id,tenant_id,pr_id,item_id,qty,estimated_price,notes) "
                        "VALUES (:id,:t,:pr,:iid,:qty,:ep,:notes)"),
                   {"id": lid, "t": t, "pr": pr_id, "iid": l.item_id,
                    "qty": l.qty, "ep": l.estimated_price, "notes": l.notes})
    audit_log(db, t, user["id"], "create", "purchase_request", pr_id)
    db.commit()
    return success_response("PR created", {"id": pr_id, "pr_number": pr_num})


@router.put("/purchase-requests/{pr_id}/approve")
def approve_purchase_request(pr_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "approve")
    t = user["tenant_id"]
    pr = db.execute(text("SELECT id, status FROM dbp_trading_purchase_requests "
                         "WHERE id=:id AND tenant_id=:t"),
                    {"id": pr_id, "t": t}).fetchone()
    if not pr:
        raise HTTPException(404, detail="PR not found")
    if pr[1] != "draft":
        raise HTTPException(400, detail=f"Cannot approve PR in status: {pr[1]}")

    db.execute(text("UPDATE dbp_trading_purchase_requests SET status='approved', "
                    "approved_by=:ab, approved_at=NOW() WHERE id=:id"),
               {"ab": user.get("email", ""), "id": pr_id})
    audit_log(db, t, user["id"], "approve", "purchase_request", pr_id)
    db.commit()
    return success_response("PR approved")


class POCreate(BaseModel):
    supplier_id: str
    sq_id: str | None = None
    pr_id: str | None = None
    expected_date: str | None = None
    tax_rate: float = 0
    notes: str | None = None
    lines: list[PRLine]


@router.post("/purchase-orders")
def create_purchase_order(body: POCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    po_id = uid()
    po_num = f"PO-{now().strftime('%Y%m%d')}-{po_id[:6].upper()}"

    subtotal = 0
    for l in body.lines:
        subtotal += l.qty * l.estimated_price
    tax_amt = subtotal * body.tax_rate / 100
    total = subtotal + tax_amt

    db.execute(text("INSERT INTO dbp_trading_purchase_orders "
                    "(id,tenant_id,po_number,supplier_id,sq_id,order_date,expected_date,"
                    "subtotal,tax_rate,tax_amount,total,notes,status,created_by) "
                    "VALUES (:id,:t,:po,:sid,:sqid,:od,:ed,:sub,:tr,:ta,:tot,:notes,'draft',:cb)"),
               {"id": po_id, "t": t, "po": po_num, "sid": body.supplier_id,
                "sqid": body.sq_id, "od": date.today(), "ed": body.expected_date,
                "sub": subtotal, "tr": body.tax_rate, "ta": tax_amt, "tot": total,
                "notes": body.notes, "cb": user.get("email", "")})
    for l in body.lines:
        lid = uid()
        lt = l.qty * l.estimated_price
        db.execute(text("INSERT INTO dbp_trading_purchase_order_lines "
                        "(id,tenant_id,po_id,item_id,qty,unit_price,line_total) "
                        "VALUES (:id,:t,:po,:iid,:qty,:up,:lt)"),
                   {"id": lid, "t": t, "po": po_id, "iid": l.item_id,
                    "qty": l.qty, "up": l.estimated_price, "lt": lt})
    audit_log(db, t, user["id"], "create", "purchase_order", po_id, new_values={"total": total})
    db.commit()
    return success_response("PO created", {"id": po_id, "po_number": po_num, "total": total})


class GRNLine(BaseModel):
    item_id: str
    qty_received: float = Field(ge=0)
    qty_accepted: float = Field(ge=0)
    unit_cost: float = Field(ge=0)
    warehouse_id: str | None = "default"
    batch_number: str | None = None


class GRNCreate(BaseModel):
    po_id: str
    lines: list[GRNLine]


@router.post("/grn")
def create_grn(body: GRNCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    po = db.execute(text("SELECT id, supplier_id, status FROM dbp_trading_purchase_orders "
                         "WHERE id=:id AND tenant_id=:t"),
                    {"id": body.po_id, "t": t}).fetchone()
    if not po:
        raise HTTPException(404, detail="PO not found")
    if po[2] == "received":
        raise HTTPException(400, detail="PO already received")

    grn_id = uid()
    grn_num = f"GRN-{now().strftime('%Y%m%d')}-{grn_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_grn "
                    "(id,tenant_id,grn_number,po_id,supplier_id,received_by,status) "
                    "VALUES (:id,:t,:gn,:po,:sid,:rb,'received')"),
               {"id": grn_id, "t": t, "gn": grn_num, "po": body.po_id,
                "sid": po[1], "rb": user.get("email", "")})

    total_cost = 0
    for l in body.lines:
        lid = uid()
        accepted = l.qty_accepted if l.qty_accepted else l.qty_received
        unit_cost = l.unit_cost
        line_cost = accepted * unit_cost
        total_cost += line_cost

        db.execute(text("INSERT INTO dbp_trading_grn_lines "
                        "(id,tenant_id,grn_id,item_id,qty_received,qty_accepted,qty_rejected,unit_cost) "
                        "VALUES (:id,:t,:grn,:iid,:qr,:qa,:qrj,:uc)"),
                   {"id": lid, "t": t, "grn": grn_id, "iid": l.item_id,
                    "qr": l.qty_received, "qa": accepted,
                    "qrj": l.qty_received - accepted, "uc": unit_cost})

        # H4: Atomic stock receive
        warehouse_id = l.warehouse_id or "default"
        atomic_stock_receive(db, t, l.item_id, accepted, unit_cost, warehouse_id,
                             stock_table="dbp_commerce_stock", item_column="item_id")

        # Update PO received_qty (with tenant isolation)
        db.execute(text("UPDATE dbp_trading_purchase_order_lines SET received_qty=received_qty+:q "
                        "WHERE po_id=:po AND item_id=:iid AND tenant_id=:t"),
                   {"q": accepted, "po": body.po_id, "iid": l.item_id, "t": t})

        # H7: Journal: Dr Inventory / Cr GRN Clearing
        company_id = get_company_id(db, t)
        post_journal(db, t, company_id, "grn",
                     f"GRN {grn_num}",
                     [{"account_code": "1300", "description": "Inventory",
                       "debit": line_cost},
                      {"account_code": "2200", "description": "GRN Clearing",
                       "credit": line_cost}])

    # Update PO status (with tenant isolation)
    db.execute(text("UPDATE dbp_trading_purchase_orders SET grn_status='received' WHERE id=:po AND tenant_id=:t"),
               {"po": body.po_id, "t": t})

    audit_log(db, t, user["id"], "create", "grn", grn_id,
              new_values={"grn_number": grn_num, "total_cost": total_cost})
    db.commit()
    return success_response("GRN processed", {"id": grn_id, "grn_number": grn_num, "total_cost": total_cost})


class PurchaseInvoiceCreate(BaseModel):
    po_id: str | None = None
    grn_id: str | None = None
    supplier_id: str
    tax_amount: float = 0
    due_days: int = 30


@router.post("/purchase-invoices")
def create_purchase_invoice(body: PurchaseInvoiceCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    # Get amounts from PO lines
    if body.po_id:
        po_lines = db.execute(text(
            "SELECT SUM(line_total) FROM dbp_trading_purchase_order_lines WHERE po_id=:po"),
            {"po": body.po_id}).fetchone()
        subtotal = float(po_lines[0] or 0)
    else:
        subtotal = 0

    total = subtotal + body.tax_amount
    inv_id = uid()
    inv_num = f"PINV-{now().strftime('%Y%m%d')}-{inv_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_purchase_invoices "
                    "(id,tenant_id,invoice_number,po_id,grn_id,supplier_id,due_date,"
                    "subtotal,tax_amount,total,balance,status,created_by) "
                    "VALUES (:id,:t,:inv,:po,:grn,:sid,:dd,:sub,:ta,:tot,:bal,'unpaid',:cb)"),
               {"id": inv_id, "t": t, "inv": inv_num, "po": body.po_id, "grn": body.grn_id,
                "sid": body.supplier_id,
                "dd": date.today() + timedelta(days=body.due_days),
                "sub": subtotal, "ta": body.tax_amount, "tot": total,
                "bal": total, "cb": user.get("email", "")})

    # H7: Journal: Dr AP Clearing / Cr AP
    company_id = get_company_id(db, t)
    journal_id = post_journal(db, t, company_id, "purchase_invoice",
                              f"Purchase Invoice {inv_num}",
                              [{"account_code": "2200", "description": "AP Clearing",
                                "debit": total},
                               {"account_code": "2100", "description": "Accounts Payable",
                                "credit": total}])

    db.execute(text("UPDATE dbp_trading_purchase_invoices SET journal_entry_id=:je WHERE id=:id"),
               {"je": journal_id, "id": inv_id})

    # Update PO invoice status (with tenant isolation)
    if body.po_id:
        db.execute(text("UPDATE dbp_trading_purchase_orders SET invoice_status='invoiced' WHERE id=:po AND tenant_id=:t"),
                   {"po": body.po_id, "t": t})

    audit_log(db, t, user["id"], "create", "purchase_invoice", inv_id, new_values={"total": total})
    db.commit()
    return success_response("Purchase invoice created", {"id": inv_id, "invoice_number": inv_num, "total": total})


class SupplierPaymentCreate(BaseModel):
    supplier_id: str
    invoice_id: str | None = None
    amount: float = Field(gt=0)
    payment_method: str = "bank_transfer"
    reference: str | None = None


@router.post("/supplier-payments")
def create_supplier_payment(body: SupplierPaymentCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    pay_id = uid()
    pay_num = f"SP-{now().strftime('%Y%m%d')}-{pay_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_supplier_payments "
                    "(id,tenant_id,payment_number,supplier_id,invoice_id,amount,payment_method,reference,created_by) "
                    "VALUES (:id,:t,:pn,:sid,:iid,:amt,:pm,:ref,:cb)"),
               {"id": pay_id, "t": t, "pn": pay_num, "sid": body.supplier_id,
                "iid": body.invoice_id, "amt": body.amount, "pm": body.payment_method,
                "ref": body.reference, "cb": user.get("email", "")})

    # Update invoice (with tenant isolation)
    if body.invoice_id:
        inv = db.execute(text("SELECT total, paid_amount FROM dbp_trading_purchase_invoices "
                              "WHERE id=:id AND tenant_id=:t"),
                         {"id": body.invoice_id, "t": t}).fetchone()
        if inv:
            new_paid = float(inv[1] or 0) + body.amount
            new_bal = float(inv[0] or 0) - new_paid
            new_status = "paid" if new_bal <= 0 else "partial"
            db.execute(text("UPDATE dbp_trading_purchase_invoices SET paid_amount=:pa, balance=:bal, status=:st "
                            "WHERE id=:id AND tenant_id=:t"),
                       {"pa": new_paid, "bal": max(new_bal, 0), "st": new_status,
                        "id": body.invoice_id, "t": t})

    # H7: Journal: Dr AP / Cr Cash
    company_id = get_company_id(db, t)
    journal_id = post_journal(db, t, company_id, "supplier_payment",
                              f"Supplier Payment {pay_num}",
                              [{"account_code": "2100", "description": "Accounts Payable",
                                "debit": body.amount},
                               {"account_code": "1100", "description": "Cash/Bank",
                                "credit": body.amount}])

    db.execute(text("UPDATE dbp_trading_supplier_payments SET journal_entry_id=:je WHERE id=:id"),
               {"je": journal_id, "id": pay_id})

    audit_log(db, t, user["id"], "create", "supplier_payment", pay_id,
              new_values={"amount": body.amount})
    db.commit()
    return success_response("Supplier payment recorded", {"id": pay_id, "payment_number": pay_num})


# ═══════════════════════════════════════════════════
# STOCK: LIST / TRANSFER / ADJUSTMENT
# ═══════════════════════════════════════════════════

@router.get("/stock")
def list_stock(user: dict | None=None, db=Depends(get_db),
               warehouse_id: str | None = None, search: str | None = None):
    check_permission(user, "read")
    t = user["tenant_id"]
    result = _ce_list_stock(db, t, page=1, page_size=1000,
                            warehouse_id=warehouse_id or "", search=search or "")
    stock = result["data"]
    for s in stock:
        s["available"] = s["on_hand"] - s["reserved"]
        s["value"] = s["on_hand"] * s["unit_cost"]
    return list_response(stock, result["total"])


class TransferLine(BaseModel):
    item_id: str
    qty: float = Field(gt=0)


class TransferCreate(BaseModel):
    from_warehouse_id: str
    to_warehouse_id: str
    notes: str | None = None
    lines: list[TransferLine]


@router.post("/stock-transfers")
def create_stock_transfer(body: TransferCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]

    if body.from_warehouse_id == body.to_warehouse_id:
        raise HTTPException(400, detail="Cannot transfer to same warehouse")

    tr_id = uid()
    tr_num = f"STK-{now().strftime('%Y%m%d')}-{tr_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_stock_transfers "
                    "(id,tenant_id,transfer_number,from_warehouse_id,to_warehouse_id,notes,status,created_by) "
                    "VALUES (:id,:t,:tn,:fw,:tw,:notes,'pending',:cb)"),
               {"id": tr_id, "t": t, "tn": tr_num, "fw": body.from_warehouse_id,
                "tw": body.to_warehouse_id, "notes": body.notes, "cb": user.get("email", "")})

    for l in body.lines:
        lid = uid()
        db.execute(text("INSERT INTO dbp_trading_stock_transfer_lines "
                        "(id,tenant_id,transfer_id,item_id,qty) VALUES (:id,:t,:ti,:iid,:qty)"),
                   {"id": lid, "t": t, "ti": tr_id, "iid": l.item_id, "qty": l.qty})

        # H4: Issue from source warehouse (get unit_cost for WAC transfer)
        stock_row = db.execute(text("SELECT unit_cost FROM dbp_commerce_stock "
                                    "WHERE tenant_id=:t AND item_id=:iid AND warehouse_id=:w"),
                               {"t": t, "iid": l.item_id, "w": body.from_warehouse_id}).fetchone()
        unit_cost = float(stock_row[0] or 0) if stock_row else 0

        atomic_stock_issue(db, t, l.item_id, l.qty, body.from_warehouse_id,
                           stock_table="dbp_commerce_stock", item_column="item_id")

        # Receive at destination with correct unit_cost (preserves WAC)
        atomic_stock_receive(db, t, l.item_id, l.qty, unit_cost, body.to_warehouse_id,
                             stock_table="dbp_commerce_stock", item_column="item_id")

    db.execute(text("UPDATE dbp_trading_stock_transfers SET status='completed' WHERE id=:id"),
               {"id": tr_id})

    audit_log(db, t, user["id"], "create", "stock_transfer", tr_id,
              new_values={"transfer_number": tr_num})
    db.commit()
    return success_response("Transfer completed", {"id": tr_id, "transfer_number": tr_num})


# ═══════════════════════════════════════════════════
# PRICING
# ═══════════════════════════════════════════════════

class PriceListCreate(BaseModel):
    list_name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_default: bool = False


@router.get("/price-lists")
def list_price_lists(user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    pls = _ce_list_price_lists(db, t)
    return list_response(pls, len(pls))


@router.post("/price-lists")
def create_price_list(body: PriceListCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    data = {"name": body.list_name, "description": body.description, "is_default": body.is_default}
    result = _ce_create_price_list(db, t, data, user_id=user["id"])
    return success_response("Price list created", {"id": result["id"]})


@router.get("/audit")
def list_audit(user: dict | None=None, db=Depends(get_db),
               page: int = 1, page_size: int = 50,
               entity_type: str | None = None):
    check_permission(user, "read")
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if entity_type:
        where += " AND entity_type=:et"
        params["et"] = entity_type

    total = db.execute(text(f"SELECT COUNT(*) FROM dbp_construction_audit {where}"), params).fetchone()[0]
    rows = db.execute(text(
        f"SELECT id, action, entity_type, entity_id, user_id, created_at "
        f"FROM dbp_construction_audit {where} ORDER BY created_at DESC "
        f"LIMIT :lim OFFSET :off"),
        {**params, "lim": page_size, "off": (page - 1) * page_size}).fetchall()

    entries = [{"id": r[0], "action": r[1], "entity_type": r[2],
                "entity_id": r[3], "user_id": r[4], "created_at": str(r[5])} for r in rows]

    return list_response(entries, total, page, page_size)


# ═══════════════════════════════════════════════════
# GET-BY-ID ENDPOINTS
# ═══════════════════════════════════════════════════

@router.get("/items/{item_id}")
def get_item(item_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    item = _ce_get_item(db, t, item_id)
    stock = db.execute(text("SELECT SUM(on_hand), SUM(reserved) FROM dbp_commerce_stock "
                            "WHERE item_id=:iid AND tenant_id=:t"),
                       {"iid": item_id, "t": t}).fetchone()
    item["on_hand"] = float(stock[0] or 0) if stock else 0
    item["reserved"] = float(stock[1] or 0) if stock else 0
    return success_response("Item", item)


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    cust = _ce_get_customer(db, t, customer_id)
    return success_response("Customer", cust)


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: str, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "read")
    t = user["tenant_id"]
    supp = _ce_get_supplier(db, t, supplier_id)
    return success_response("Supplier", supp)


# ═══════════════════════════════════════════════════
# STOCK ADJUSTMENTS
# ═══════════════════════════════════════════════════

class StockAdjustmentLine(BaseModel):
    item_id: str
    qty_after: float = Field(ge=0)


class StockAdjustmentCreate(BaseModel):
    warehouse_id: str
    reason: str = Field(min_length=1)
    lines: list[StockAdjustmentLine]


@router.post("/stock-adjustments")
def create_stock_adjustment(body: StockAdjustmentCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    adj_id = uid()
    adj_num = f"SA-{now().strftime('%Y%m%d')}-{adj_id[:6].upper()}"

    db.execute(text("INSERT INTO dbp_trading_stock_adjustments "
                    "(id,tenant_id,adj_number,warehouse_id,reason,status,created_by) "
                    "VALUES (:id,:t,:an,:wid,:reason,'pending',:cb)"),
               {"id": adj_id, "t": t, "an": adj_num, "wid": body.warehouse_id,
                "reason": body.reason, "cb": user.get("email", "")})

    for l in body.lines:
        lid = uid()
        # Get current qty (Fixed H15: consolidated to dbp_commerce_stock)
        stock = db.execute(text("SELECT id, on_hand, unit_cost FROM dbp_commerce_stock "
                                "WHERE tenant_id=:t AND item_id=:iid AND warehouse_id=:w FOR UPDATE"),
                           {"t": t, "iid": l.item_id, "w": body.warehouse_id}).fetchone()
        qty_before = float(stock[1] or 0) if stock else 0
        unit_cost = float(stock[2] or 0) if stock else 0
        qty_adjusted = l.qty_after - qty_before

        db.execute(text("INSERT INTO dbp_trading_stock_adjustment_lines "
                        "(id,tenant_id,adjustment_id,item_id,qty_before,qty_after,qty_adjusted,unit_cost) "
                        "VALUES (:id,:t,:aid,:iid,:qb,:qa,:qadj,:uc)"),
                   {"id": lid, "t": t, "aid": adj_id, "iid": l.item_id,
                    "qb": qty_before, "qa": l.qty_after, "qadj": qty_adjusted, "uc": unit_cost})

        # Update stock (Fixed H15: consolidated to dbp_commerce_stock)
        if stock:
            db.execute(text("UPDATE dbp_commerce_stock SET on_hand=:q WHERE id=:sid"),
                       {"q": l.qty_after, "sid": stock[0]})
        else:
            sid = uid()
            db.execute(text("INSERT INTO dbp_commerce_stock "
                            "(id, tenant_id, item_id, warehouse_id, on_hand, reserved, unit_cost, created_at) "
                            "VALUES (:id, :t, :iid, :w, :q, 0, :uc, :now)"),
                       {"id": sid, "t": t, "iid": l.item_id, "w": body.warehouse_id,
                        "q": l.qty_after, "uc": unit_cost, "now": now()})

        # Journal if value changed
        value_change = qty_adjusted * unit_cost
        if abs(value_change) > 0.01:
            company_id = get_company_id(db, t)
            if value_change > 0:
                post_journal(db, t, company_id, "stock_adjustment",
                             f"SA {adj_num} — Increase",
                             [{"account_code": "1300", "description": "Inventory", "debit": value_change},
                              {"account_code": "5200", "description": "Inventory Adjustment", "credit": value_change}])
            else:
                post_journal(db, t, company_id, "stock_adjustment",
                             f"SA {adj_num} — Decrease",
                             [{"account_code": "5200", "description": "Inventory Adjustment", "debit": abs(value_change)},
                              {"account_code": "1300", "description": "Inventory", "credit": abs(value_change)}])

    db.execute(text("UPDATE dbp_trading_stock_adjustments SET status='approved', approved_by=:ab WHERE id=:id"),
               {"ab": user.get("email", ""), "id": adj_id})

    audit_log(db, t, user["id"], "create", "stock_adjustment", adj_id,
              new_values={"adj_number": adj_num, "reason": body.reason})
    db.commit()
    return success_response("Stock adjustment processed", {"id": adj_id, "adj_number": adj_num})


@router.get("/stock-adjustments")
def list_stock_adjustments(user: dict | None=None, db=Depends(get_db),
                           page: int = 1, page_size: int = 50):
    check_permission(user, "read")
    t = user["tenant_id"]
    total = db.execute(text("SELECT COUNT(*) FROM dbp_trading_stock_adjustments WHERE tenant_id=:t"),
                       {"t": t}).fetchone()[0]
    rows = db.execute(text(
        "SELECT id, adj_number, warehouse_id, reason, status, created_by, created_at "
        "FROM dbp_trading_stock_adjustments WHERE tenant_id=:t ORDER BY created_at DESC "
        "LIMIT :lim OFFSET :off"),
        {"t": t, "lim": page_size, "off": (page - 1) * page_size}).fetchall()
    items = [{"id": r[0], "adj_number": r[1], "warehouse_id": r[2], "reason": r[3],
              "status": r[4], "created_by": r[5], "created_at": str(r[6])} for r in rows]
    return list_response(items, total, page, page_size)
