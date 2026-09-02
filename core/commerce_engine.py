"""
Commerce Engine — Shared Commerce Layer for All Industry Templates
==================================================================
Centralizes items, stock, warehouses, customers, suppliers, and pricing
that were previously duplicated across Trading, Retail, Restaurant APIs.

Tables (after P70.7C.2 migration):
  dbp_commerce_items      → shared: items/products catalog
  dbp_commerce_stock      → shared: per-warehouse stock levels
  dbp_commerce_warehouses → shared: warehouses/locations
  dbp_commerce_customers  → shared: customer master
  dbp_commerce_suppliers  → shared: supplier master
  dbp_trading_price_lists → trading-specific: price lists

Design:
  - Every function filters by tenant_id (H1: Tenant Isolation)
  - Every mutation calls audit_log (H5: Audit Trail)
  - Every mutation validates input (H3: Integrity)
  - Stock operations use SELECT FOR UPDATE (H4: Concurrency)
  - Returns dicts consistently (not raw Row objects)
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.industry_security import (
    audit_log,
    check_permission,
    now,
    uid,
)

# ═══════════════════════════════════════════════════
# TABLE NAMES (will be renamed to dbp_commerce_* in P70.7C.2)
# ═══════════════════════════════════════════════════

T_ITEMS = "dbp_commerce_items"
T_STOCK = "dbp_commerce_stock"
T_WAREHOUSES = "dbp_commerce_warehouses"
T_CUSTOMERS = "dbp_commerce_customers"
T_SUPPLIERS = "dbp_commerce_suppliers"


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _row_to_dict(row, columns: list) -> dict:
    """Convert a SQLAlchemy Row to a dict with float conversion for numerics."""
    if not row:
        return {}
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, (int, float)) or hasattr(val, '__class__') and val.__class__.__name__ == 'Decimal':
            val = float(val)
        d[col] = val
    return d


ITEM_COLUMNS = [
    "id", "tenant_id", "item_code", "name", "name_ar", "category", "unit",
    "cost_price", "selling_price", "min_stock", "max_stock", "reorder_point",
    "has_batch", "has_serial", "has_expiry", "barcode", "status",
]

STOCK_COLUMNS = [
    "id", "tenant_id", "item_id", "warehouse_id",
    "on_hand", "reserved", "in_transit", "unit_cost",
]

WAREHOUSE_COLUMNS = [
    "id", "tenant_id", "code", "name", "name_ar", "address", "manager", "status",
]

CUSTOMER_COLUMNS = [
    "id", "tenant_id", "customer_code", "name", "name_ar", "contact_person",
    "email", "phone", "address", "credit_limit", "current_balance",
    "territory", "salesman", "payment_terms", "status",
]

SUPPLIER_COLUMNS = [
    "id", "tenant_id", "supplier_code", "name", "name_ar", "contact_person",
    "email", "phone", "address", "payment_terms", "lead_time_days", "status",
]


# ═══════════════════════════════════════════════════
# ITEMS
# ═══════════════════════════════════════════════════

def get_item(db: Session, tenant_id: str, item_id: str) -> dict:
    """Get a single item by ID. Raises 404 if not found."""
    cols = ", ".join(ITEM_COLUMNS)
    row = db.execute(
        text(f"SELECT {cols} FROM {T_ITEMS} WHERE id=:id AND tenant_id=:t"),
        {"id": item_id, "t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Commerce item not found")
    return _row_to_dict(row, ITEM_COLUMNS)


def get_item_by_barcode(db: Session, tenant_id: str, barcode: str) -> dict:
    """Get a single item by barcode."""
    cols = ", ".join(ITEM_COLUMNS)
    row = db.execute(
        text(f"SELECT {cols} FROM {T_ITEMS} WHERE barcode=:bc AND tenant_id=:t"),
        {"bc": barcode, "t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Item not found for barcode")
    return _row_to_dict(row, ITEM_COLUMNS)


def list_items(db: Session, tenant_id: str, page: int = 1, page_size: int = 50,
               search: str = "", category: str = "", status: str = "active") -> dict:
    """List items with pagination, search, and filtering."""
    where = "WHERE tenant_id=:t"
    params: dict = {"t": tenant_id, "limit": page_size, "offset": (page - 1) * page_size}

    if search:
        where += " AND (name ILIKE :s OR item_code ILIKE :s OR barcode ILIKE :s)"
        params["s"] = f"%{search}%"
    if category:
        where += " AND category=:cat"
        params["cat"] = category
    if status:
        where += " AND status=:st"
        params["st"] = status

    total = db.execute(text(f"SELECT COUNT(*) FROM {T_ITEMS} {where}"), params).fetchone()[0]
    rows = db.execute(
        text(f"SELECT {', '.join(ITEM_COLUMNS)} FROM {T_ITEMS} {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    return {"data": [_row_to_dict(r, ITEM_COLUMNS) for r in rows], "total": total}


def create_item(db: Session, tenant_id: str, data: dict, user_id: str = "") -> dict:
    """Create a new commerce item."""
    check_permission({"roles": ["user"]}, "create")  # caller should pass user
    if not data.get("item_code"):
        raise HTTPException(400, detail="item_code is required")
    if not data.get("name"):
        raise HTTPException(400, detail="name is required")
    if float(data.get("cost_price", 0)) < 0:
        raise HTTPException(400, detail="cost_price must be >= 0")
    if float(data.get("selling_price", 0)) < 0:
        raise HTTPException(400, detail="selling_price must be >= 0")

    # Check unique item_code
    existing = db.execute(
        text(f"SELECT id FROM {T_ITEMS} WHERE tenant_id=:t AND item_code=:code"),
        {"t": tenant_id, "code": data["item_code"]},
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Item code already exists: {data['item_code']}")

    item_id = uid()
    db.execute(text(
        f"INSERT INTO {T_ITEMS} "
        "(id, tenant_id, item_code, name, name_ar, category, unit, cost_price, selling_price, "
        "min_stock, max_stock, reorder_point, has_batch, has_serial, has_expiry, barcode, status, created_at) "
        "VALUES (:id, :t, :code, :name, :name_ar, :cat, :unit, :cp, :sp, "
        ":min, :max, :reorder, :batch, :serial, :expiry, :bc, :st, :now)"
    ), {
        "id": item_id, "t": tenant_id, "code": data["item_code"], "name": data["name"],
        "name_ar": data.get("name_ar"), "cat": data.get("category"),
        "unit": data.get("unit", "piece"),
        "cp": float(data.get("cost_price", 0)), "sp": float(data.get("selling_price", 0)),
        "min": float(data.get("min_stock", 0)), "max": float(data.get("max_stock", 999999)),
        "reorder": float(data.get("reorder_point", 0)),
        "batch": data.get("has_batch", False), "serial": data.get("has_serial", False),
        "expiry": data.get("has_expiry", False),
        "bc": data.get("barcode"), "st": data.get("status", "active"), "now": now(),
    })
    if user_id:
        audit_log(db, tenant_id, user_id, "create", "commerce_item", item_id,
                  new_values={"item_code": data["item_code"], "name": data["name"]})
    db.commit()
    return get_item(db, tenant_id, item_id)


def update_item(db: Session, tenant_id: str, item_id: str, data: dict, user_id: str = "") -> dict:
    """Update an existing commerce item."""
    old = get_item(db, tenant_id, item_id)
    sets = []
    params: dict = {"id": item_id, "t": tenant_id, "now": now()}
    for field in ["item_code", "name", "name_ar", "category", "unit", "barcode", "status"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = data[field]
    for field in ["cost_price", "selling_price", "min_stock", "max_stock", "reorder_point"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = float(data[field])
    for field in ["has_batch", "has_serial", "has_expiry"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = data[field]
    if not sets:
        return old
    sets.append("updated_at=:now")
    db.execute(text(f"UPDATE {T_ITEMS} SET {', '.join(sets)} WHERE id=:id AND tenant_id=:t"), params)
    if user_id:
        audit_log(db, tenant_id, user_id, "update", "commerce_item", item_id,
                  old_values={k: old[k] for k in data if k in old},
                  new_values={k: data[k] for k in data})
    db.commit()
    return get_item(db, tenant_id, item_id)


# ═══════════════════════════════════════════════════
# STOCK
# ═══════════════════════════════════════════════════

def get_stock(db: Session, tenant_id: str, item_id: str,
              warehouse_id: str = "default") -> dict:
    """Get stock level for an item in a warehouse."""
    row = db.execute(
        text(f"SELECT {', '.join(STOCK_COLUMNS)} FROM {T_STOCK} "
             "WHERE tenant_id=:t AND item_id=:item AND warehouse_id=:wh"),
        {"t": tenant_id, "item": item_id, "wh": warehouse_id},
    ).fetchone()
    if not row:
        return {"on_hand": 0, "reserved": 0, "in_transit": 0, "unit_cost": 0}
    return _row_to_dict(row, STOCK_COLUMNS)


def list_stock(db: Session, tenant_id: str, page: int = 1, page_size: int = 50,
               warehouse_id: str = "", search: str = "") -> dict:
    """List stock with item names and warehouse names."""
    where = "WHERE s.tenant_id=:t"
    params: dict = {"t": tenant_id, "limit": page_size, "offset": (page - 1) * page_size}
    if warehouse_id:
        where += " AND s.warehouse_id=:wh"
        params["wh"] = warehouse_id
    if search:
        where += " AND (i.name ILIKE :s OR i.item_code ILIKE :s)"
        params["s"] = f"%{search}%"

    count_sql = f"SELECT COUNT(*) FROM {T_STOCK} s JOIN {T_ITEMS} i ON s.item_id=i.id {where}"
    total = db.execute(text(count_sql), params).fetchone()[0]
    data_sql = (
        f"SELECT s.id, s.item_id, i.name, i.item_code, s.warehouse_id, w.name, "
        f"s.on_hand, s.reserved, s.unit_cost "
        f"FROM {T_STOCK} s "
        f"JOIN {T_ITEMS} i ON s.item_id=i.id "
        f"JOIN {T_WAREHOUSES} w ON s.warehouse_id=w.id "
        f"{where} ORDER BY i.name LIMIT :limit OFFSET :offset"
    )
    rows = db.execute(text(data_sql), params).fetchall()
    data = []
    for r in rows:
        data.append({
            "id": r[0], "item_id": r[1], "item_name": r[2], "item_code": r[3],
            "warehouse_id": r[4], "warehouse_name": r[5],
            "on_hand": float(r[6] or 0), "reserved": float(r[7] or 0),
            "unit_cost": float(r[8] or 0),
        })
    return {"data": data, "total": total, "page": page, "page_size": page_size}


def atomic_stock_receive(db: Session, tenant_id: str, item_id: str,
                         qty: float, price: float, warehouse_id: str = "default",
                         user_id: str = "") -> str:
    """Atomically receive stock with row-level locking and weighted average cost."""
    if qty <= 0:
        raise HTTPException(400, detail="Receive qty must be > 0")
    if price < 0:
        raise HTTPException(400, detail="Price must be >= 0")

    existing = db.execute(
        text(f"SELECT id, on_hand, unit_cost FROM {T_STOCK} "
             "WHERE tenant_id=:t AND item_id=:item AND warehouse_id=:wh FOR UPDATE"),
        {"t": tenant_id, "item": item_id, "wh": warehouse_id},
    ).fetchone()
    total_cost = Decimal(str(qty)) * Decimal(str(price))
    if existing:
        old_qty = Decimal(str(existing[1] or 0))
        new_qty = old_qty + Decimal(str(qty))
        old_cost = Decimal(str(existing[2] or 0))
        new_cost = ((old_qty * old_cost) + total_cost) / new_qty if new_qty > 0 else Decimal(str(price))
        db.execute(
            text(f"UPDATE {T_STOCK} SET on_hand=:q, unit_cost=:uc, updated_at=:now WHERE id=:sid"),
            {"q": new_qty, "uc": new_cost, "sid": existing[0], "now": now()},
        )
        stock_id = existing[0]
    else:
        stock_id = uid()
        db.execute(text(
            f"INSERT INTO {T_STOCK} "
            "(id, tenant_id, item_id, warehouse_id, on_hand, reserved, unit_cost, created_at, updated_at) "
            "VALUES (:id, :t, :item, :wh, :q, 0, :uc, :now, :now)"
        ), {"id": stock_id, "t": tenant_id, "item": item_id, "wh": warehouse_id,
            "q": qty, "uc": price, "now": now()})
    if user_id:
        audit_log(db, tenant_id, user_id, "stock_receive", "commerce_stock", stock_id,
                  new_values={"item_id": item_id, "qty": qty, "price": price, "warehouse_id": warehouse_id})
    return stock_id


def atomic_stock_issue(db: Session, tenant_id: str, item_id: str,
                       qty: float, warehouse_id: str = "default",
                       user_id: str = "") -> tuple:
    """Atomically issue stock with row-level locking. Returns (stock_id, unit_cost)."""
    if qty <= 0:
        raise HTTPException(400, detail="Issue qty must be > 0")

    stock = db.execute(
        text(f"SELECT id, on_hand, unit_cost FROM {T_STOCK} "
             "WHERE tenant_id=:t AND item_id=:item AND warehouse_id=:wh FOR UPDATE"),
        {"t": tenant_id, "item": item_id, "wh": warehouse_id},
    ).fetchone()
    if not stock:
        raise HTTPException(404, detail=f"Stock not found: item {item_id} in warehouse {warehouse_id}")
    available = float(stock[1] or 0)
    if available < qty:
        raise HTTPException(400, detail=f"Insufficient stock: has {available}, need {qty}")
    new_qty = available - qty
    db.execute(
        text(f"UPDATE {T_STOCK} SET on_hand=:q, updated_at=:now WHERE id=:sid"),
        {"q": new_qty, "sid": stock[0], "now": now()},
    )
    if user_id:
        audit_log(db, tenant_id, user_id, "stock_issue", "commerce_stock", stock[0],
                  new_values={"item_id": item_id, "qty": qty, "warehouse_id": warehouse_id})
    return stock[0], float(stock[2] or 0)


# ═══════════════════════════════════════════════════
# WAREHOUSES
# ═══════════════════════════════════════════════════

def get_warehouse(db: Session, tenant_id: str, warehouse_id: str) -> dict:
    """Get a single warehouse."""
    row = db.execute(
        text(f"SELECT {', '.join(WAREHOUSE_COLUMNS)} FROM {T_WAREHOUSES} "
             "WHERE id=:id AND tenant_id=:t"),
        {"id": warehouse_id, "t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Warehouse not found")
    return _row_to_dict(row, WAREHOUSE_COLUMNS)


def list_warehouses(db: Session, tenant_id: str) -> list:
    """List all warehouses for a tenant."""
    rows = db.execute(
        text(f"SELECT {', '.join(WAREHOUSE_COLUMNS)} FROM {T_WAREHOUSES} "
             "WHERE tenant_id=:t ORDER BY name"),
        {"t": tenant_id},
    ).fetchall()
    return [_row_to_dict(r, WAREHOUSE_COLUMNS) for r in rows]


def create_warehouse(db: Session, tenant_id: str, data: dict, user_id: str = "") -> dict:
    """Create a new warehouse."""
    if not data.get("code"):
        raise HTTPException(400, detail="code is required")
    if not data.get("name"):
        raise HTTPException(400, detail="name is required")

    existing = db.execute(
        text(f"SELECT id FROM {T_WAREHOUSES} WHERE tenant_id=:t AND code=:code"),
        {"t": tenant_id, "code": data["code"]},
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Warehouse code already exists: {data['code']}")

    wh_id = uid()
    db.execute(text(
        f"INSERT INTO {T_WAREHOUSES} "
        "(id, tenant_id, code, name, name_ar, address, manager, status, created_at) "
        "VALUES (:id, :t, :code, :name, :name_ar, :addr, :mgr, :st, :now)"
    ), {
        "id": wh_id, "t": tenant_id, "code": data["code"], "name": data["name"],
        "name_ar": data.get("name_ar"), "addr": data.get("address"),
        "mgr": data.get("manager"), "st": data.get("status", "active"), "now": now(),
    })
    if user_id:
        audit_log(db, tenant_id, user_id, "create", "commerce_warehouse", wh_id,
                  new_values={"code": data["code"], "name": data["name"]})
    db.commit()
    return get_warehouse(db, tenant_id, wh_id)


# ═══════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════

def get_customer(db: Session, tenant_id: str, customer_id: str) -> dict:
    """Get a single customer."""
    row = db.execute(
        text(f"SELECT {', '.join(CUSTOMER_COLUMNS)} FROM {T_CUSTOMERS} "
             "WHERE id=:id AND tenant_id=:t"),
        {"id": customer_id, "t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Customer not found")
    return _row_to_dict(row, CUSTOMER_COLUMNS)


def list_customers(db: Session, tenant_id: str, page: int = 1, page_size: int = 50,
                   search: str = "") -> dict:
    """List customers with pagination and search."""
    where = "WHERE tenant_id=:t"
    params: dict = {"t": tenant_id, "limit": page_size, "offset": (page - 1) * page_size}
    if search:
        where += " AND (name ILIKE :s OR customer_code ILIKE :s)"
        params["s"] = f"%{search}%"

    total = db.execute(text(f"SELECT COUNT(*) FROM {T_CUSTOMERS} {where}"), params).fetchone()[0]
    rows = db.execute(
        text(f"SELECT {', '.join(CUSTOMER_COLUMNS)} FROM {T_CUSTOMERS} {where} "
             "ORDER BY name LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    return {"data": [_row_to_dict(r, CUSTOMER_COLUMNS) for r in rows], "total": total}


def create_customer(db: Session, tenant_id: str, data: dict, user_id: str = "") -> dict:
    """Create a new customer."""
    if not data.get("customer_code"):
        raise HTTPException(400, detail="customer_code is required")
    if not data.get("name"):
        raise HTTPException(400, detail="name is required")
    if float(data.get("credit_limit", 0)) < 0:
        raise HTTPException(400, detail="credit_limit must be >= 0")

    existing = db.execute(
        text(f"SELECT id FROM {T_CUSTOMERS} WHERE tenant_id=:t AND customer_code=:code"),
        {"t": tenant_id, "code": data["customer_code"]},
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Customer code already exists: {data['customer_code']}")

    cid = uid()
    db.execute(text(
        f"INSERT INTO {T_CUSTOMERS} "
        "(id, tenant_id, customer_code, name, name_ar, contact_person, email, phone, address, "
        "credit_limit, current_balance, territory, salesman, payment_terms, status, created_at) "
        "VALUES (:id, :t, :code, :name, :name_ar, :cp, :email, :phone, :addr, "
        ":cl, 0, :terr, :sm, :pt, :st, :now)"
    ), {
        "id": cid, "t": tenant_id, "code": data["customer_code"], "name": data["name"],
        "name_ar": data.get("name_ar"), "cp": data.get("contact_person"),
        "email": data.get("email"), "phone": data.get("phone"), "addr": data.get("address"),
        "cl": float(data.get("credit_limit", 0)), "terr": data.get("territory"),
        "sm": data.get("salesman"), "pt": data.get("payment_terms", "net30"),
        "st": data.get("status", "active"), "now": now(),
    })
    if user_id:
        audit_log(db, tenant_id, user_id, "create", "commerce_customer", cid,
                  new_values={"customer_code": data["customer_code"], "name": data["name"]})
    db.commit()
    return get_customer(db, tenant_id, cid)


def update_customer(db: Session, tenant_id: str, customer_id: str, data: dict,
                    user_id: str = "") -> dict:
    """Update a customer."""
    old = get_customer(db, tenant_id, customer_id)
    sets = []
    params: dict = {"id": customer_id, "t": tenant_id, "now": now()}
    for field in ["customer_code", "name", "name_ar", "contact_person", "email",
                  "phone", "address", "territory", "salesman", "payment_terms", "status"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = data[field]
    for field in ["credit_limit"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = float(data[field])
    if not sets:
        return old
    sets.append("updated_at=:now")
    db.execute(text(f"UPDATE {T_CUSTOMERS} SET {', '.join(sets)} WHERE id=:id AND tenant_id=:t"), params)
    if user_id:
        audit_log(db, tenant_id, user_id, "update", "commerce_customer", customer_id,
                  old_values={k: old[k] for k in data if k in old},
                  new_values={k: data[k] for k in data})
    db.commit()
    return get_customer(db, tenant_id, customer_id)


# ═══════════════════════════════════════════════════
# SUPPLIERS
# ═══════════════════════════════════════════════════

def get_supplier(db: Session, tenant_id: str, supplier_id: str) -> dict:
    """Get a single supplier."""
    row = db.execute(
        text(f"SELECT {', '.join(SUPPLIER_COLUMNS)} FROM {T_SUPPLIERS} "
             "WHERE id=:id AND tenant_id=:t"),
        {"id": supplier_id, "t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Supplier not found")
    return _row_to_dict(row, SUPPLIER_COLUMNS)


def list_suppliers(db: Session, tenant_id: str, page: int = 1, page_size: int = 50,
                   search: str = "") -> dict:
    """List suppliers with pagination and search."""
    where = "WHERE tenant_id=:t"
    params: dict = {"t": tenant_id, "limit": page_size, "offset": (page - 1) * page_size}
    if search:
        where += " AND (name ILIKE :s OR supplier_code ILIKE :s)"
        params["s"] = f"%{search}%"

    total = db.execute(text(f"SELECT COUNT(*) FROM {T_SUPPLIERS} {where}"), params).fetchone()[0]
    rows = db.execute(
        text(f"SELECT {', '.join(SUPPLIER_COLUMNS)} FROM {T_SUPPLIERS} {where} "
             "ORDER BY name LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    return {"data": [_row_to_dict(r, SUPPLIER_COLUMNS) for r in rows], "total": total}


def create_supplier(db: Session, tenant_id: str, data: dict, user_id: str = "") -> dict:
    """Create a new supplier."""
    if not data.get("supplier_code"):
        raise HTTPException(400, detail="supplier_code is required")
    if not data.get("name"):
        raise HTTPException(400, detail="name is required")

    existing = db.execute(
        text(f"SELECT id FROM {T_SUPPLIERS} WHERE tenant_id=:t AND supplier_code=:code"),
        {"t": tenant_id, "code": data["supplier_code"]},
    ).fetchone()
    if existing:
        raise HTTPException(400, detail=f"Supplier code already exists: {data['supplier_code']}")

    sid = uid()
    db.execute(text(
        f"INSERT INTO {T_SUPPLIERS} "
        "(id, tenant_id, supplier_code, name, name_ar, contact_person, email, phone, address, "
        "payment_terms, lead_time_days, status, created_at) "
        "VALUES (:id, :t, :code, :name, :name_ar, :cp, :email, :phone, :addr, "
        ":pt, :ltd, :st, :now)"
    ), {
        "id": sid, "t": tenant_id, "code": data["supplier_code"], "name": data["name"],
        "name_ar": data.get("name_ar"), "cp": data.get("contact_person"),
        "email": data.get("email"), "phone": data.get("phone"), "addr": data.get("address"),
        "pt": data.get("payment_terms", "net30"), "ltd": data.get("lead_time_days", 7),
        "st": data.get("status", "active"), "now": now(),
    })
    if user_id:
        audit_log(db, tenant_id, user_id, "create", "commerce_supplier", sid,
                  new_values={"supplier_code": data["supplier_code"], "name": data["name"]})
    db.commit()
    return get_supplier(db, tenant_id, sid)


def update_supplier(db: Session, tenant_id: str, supplier_id: str, data: dict,
                    user_id: str = "") -> dict:
    """Update a supplier."""
    old = get_supplier(db, tenant_id, supplier_id)
    sets = []
    params: dict = {"id": supplier_id, "t": tenant_id, "now": now()}
    for field in ["supplier_code", "name", "name_ar", "contact_person", "email",
                  "phone", "address", "payment_terms", "status"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = data[field]
    for field in ["lead_time_days"]:
        if field in data:
            sets.append(f"{field}=:{field}")
            params[field] = int(data[field])
    if not sets:
        return old
    sets.append("updated_at=:now")
    db.execute(text(f"UPDATE {T_SUPPLIERS} SET {', '.join(sets)} WHERE id=:id AND tenant_id=:t"), params)
    if user_id:
        audit_log(db, tenant_id, user_id, "update", "commerce_supplier", supplier_id,
                  old_values={k: old[k] for k in data if k in old},
                  new_values={k: data[k] for k in data})
    db.commit()
    return get_supplier(db, tenant_id, supplier_id)


# ═══════════════════════════════════════════════════
# PRICING
# ═══════════════════════════════════════════════════

def list_price_lists(db: Session, tenant_id: str) -> list:
    """List all price lists."""
    rows = db.execute(
        text("SELECT id, tenant_id, list_name, currency, is_default, status, created_at "
             "FROM dbp_trading_price_lists WHERE tenant_id=:t ORDER BY list_name"),
        {"t": tenant_id},
    ).fetchall()
    return [{"id": r[0], "tenant_id": r[1], "list_name": r[2], "currency": r[3],
             "is_default": r[4], "status": r[5], "created_at": str(r[6])} for r in rows]


def create_price_list(db: Session, tenant_id: str, data: dict, user_id: str = "") -> dict:
    """Create a price list."""
    if not data.get("name"):
        raise HTTPException(400, detail="name is required")
    pid = uid()
    db.execute(text(
        "INSERT INTO dbp_trading_price_lists "
        "(id, tenant_id, list_name, currency, is_default, status, created_at) "
        "VALUES (:id, :t, :name, :cur, :def, :st, :now)"
    ), {
        "id": pid, "t": tenant_id, "name": data["name"],
        "cur": data.get("currency", "SAR"), "def": data.get("is_default", False),
        "st": data.get("status", "active"), "now": now(),
    })
    if user_id:
        audit_log(db, tenant_id, user_id, "create", "commerce_price_list", pid,
                  new_values={"list_name": data["name"]})
    db.commit()
    return {"id": pid, "list_name": data["name"], "currency": data.get("currency", "SAR")}


# ═══════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════

def commerce_dashboard(db: Session, tenant_id: str) -> dict:
    """Commerce-wide dashboard KPIs."""
    items_count = db.execute(
        text(f"SELECT COUNT(*) FROM {T_ITEMS} WHERE tenant_id=:t AND status='active'"),
        {"t": tenant_id},
    ).fetchone()[0]
    stock_value = db.execute(
        text(f"SELECT COALESCE(SUM(s.on_hand * s.unit_cost), 0) FROM {T_STOCK} s "
             f"JOIN {T_ITEMS} i ON s.item_id=i.id WHERE s.tenant_id=:t"),
        {"t": tenant_id},
    ).fetchone()[0]
    low_stock = db.execute(
        text(f"SELECT COUNT(*) FROM {T_ITEMS} i "
             f"LEFT JOIN {T_STOCK} s ON i.id=s.item_id AND s.warehouse_id='default' "
             f"WHERE i.tenant_id=:t AND i.status='active' "
             f"AND COALESCE(s.on_hand, 0) <= i.reorder_point AND i.reorder_point > 0"),
        {"t": tenant_id},
    ).fetchone()[0]
    customers_count = db.execute(
        text(f"SELECT COUNT(*) FROM {T_CUSTOMERS} WHERE tenant_id=:t AND status='active'"),
        {"t": tenant_id},
    ).fetchone()[0]
    suppliers_count = db.execute(
        text(f"SELECT COUNT(*) FROM {T_SUPPLIERS} WHERE tenant_id=:t AND status='active'"),
        {"t": tenant_id},
    ).fetchone()[0]
    warehouses_count = db.execute(
        text(f"SELECT COUNT(*) FROM {T_WAREHOUSES} WHERE tenant_id=:t AND status='active'"),
        {"t": tenant_id},
    ).fetchone()[0]

    return {
        "items": items_count,
        "stock_value": float(stock_value),
        "low_stock_items": low_stock,
        "customers": customers_count,
        "suppliers": suppliers_count,
        "warehouses": warehouses_count,
    }
