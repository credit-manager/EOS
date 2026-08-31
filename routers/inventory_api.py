"""
EOS Inventory API Router — /api/v1/inventory
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import get_current_user

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory API"])


@router.get("/products")
async def list_products(
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    low_stock: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if category_id:
        conditions.append("category_id = :cid")
        params["cid"] = category_id
    if search:
        conditions.append("(name ILIKE :search OR sku ILIKE :search OR name_ar ILIKE :search)")
        params["search"] = f"%{search}%"
    if is_active is not None:
        conditions.append("is_active = :active")
        params["active"] = is_active
    if low_stock:
        conditions.append("current_stock <= min_stock AND min_stock > 0")
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM products WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset
    rows = db.execute(
        text(f"SELECT id, sku, name, name_ar, description, category_id, unit_price, cost_price, "
             f"currency, current_stock, min_stock, max_stock, barcode, is_active, created_at "
             f"FROM products WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()

    data = [{"id": r[0], "sku": r[1], "name": r[2], "name_ar": r[3], "description": r[4],
             "category_id": r[5], "unit_price": float(r[6]) if r[6] else 0,
             "cost_price": float(r[7]) if r[7] else 0, "currency": r[8] or "SAR",
             "current_stock": r[9] or 0, "min_stock": r[10] or 0, "max_stock": r[11] or 0,
             "barcode": r[12], "is_active": r[13] if r[13] is not None else True,
             "created_at": r[14].isoformat() if r[14] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/products/{product_id}")
async def get_product(product_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.execute(
        text("SELECT id, sku, name, name_ar, description, category_id, unit_price, cost_price, "
             "currency, current_stock, min_stock, max_stock, barcode, is_active, created_at "
             "FROM products WHERE id = :id"), {"id": product_id}
    ).fetchone()
    if not r:
        raise HTTPException(404, detail="Product not found")
    return {"id": r[0], "sku": r[1], "name": r[2], "name_ar": r[3], "description": r[4],
            "category_id": r[5], "unit_price": float(r[6]) if r[6] else 0,
            "cost_price": float(r[7]) if r[7] else 0, "currency": r[8] or "SAR",
            "current_stock": r[9] or 0, "min_stock": r[10] or 0, "max_stock": r[11] or 0,
            "barcode": r[12], "is_active": r[13] if r[13] is not None else True,
            "created_at": r[14].isoformat() if r[14] else None}


@router.post("/products", status_code=201)
async def create_product(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail="name required")
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO products (id, sku, name, name_ar, description, category_id, "
             "unit_price, cost_price, currency, current_stock, min_stock, max_stock, barcode, is_active, created_at) "
             "VALUES (:id, :sku, :name, :name_ar, :desc, :cat, :up, :cp, :cur, :stock, :min, :max, :bc, true, :now)"),
        {"id": pid, "sku": body.get("sku", f"SKU-{pid[:8].upper()}"), "name": body["name"],
         "name_ar": body.get("name_ar"), "desc": body.get("description"), "cat": body.get("category_id"),
         "up": body.get("unit_price", 0), "cp": body.get("cost_price", 0),
         "cur": body.get("currency", "SAR"), "stock": body.get("current_stock", 0),
         "min": body.get("min_stock", 0), "max": body.get("max_stock", 0),
         "bc": body.get("barcode"), "now": now},
    )
    db.commit()
    return {"id": pid, "name": body["name"], "message": "Product created"}


@router.put("/products/{product_id}")
async def update_product(product_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM products WHERE id = :id"), {"id": product_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Product not found")
    fields, params = [], {"id": product_id}
    for col in ("name", "name_ar", "description", "category_id", "sku", "barcode", "currency"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    for col in ("unit_price", "cost_price", "current_stock", "min_stock", "max_stock"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if "is_active" in body:
        fields.append("is_active = :active")
        params["active"] = body["is_active"]
    if fields:
        db.execute(text(f"UPDATE products SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Product updated"}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM products WHERE id = :id"), {"id": product_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Product not found")
    db.commit()
    return {"message": "Product deleted"}


# ─── Warehouses ─────────────────────────────────

@router.get("/warehouses")
async def list_warehouses(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, code, name, name_ar, address, address_ar, is_active, created_at FROM warehouses ORDER BY name")).fetchall()
    return [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3],
             "address": r[4], "address_ar": r[5], "is_active": r[6] if r[6] is not None else True,
             "created_at": r[7].isoformat() if r[7] else None} for r in rows]


@router.post("/warehouses", status_code=201)
async def create_warehouse(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    wid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO warehouses (id, code, name, name_ar, address, address_ar, is_active, created_at) "
             "VALUES (:id, :code, :name, :name_ar, :addr, :addr_ar, true, :now)"),
        {"id": wid, "code": body.get("code", f"WH-{wid[:6].upper()}"), "name": body.get("name", "Warehouse"),
         "name_ar": body.get("name_ar"), "addr": body.get("address"), "addr_ar": body.get("address_ar"), "now": now},
    )
    db.commit()
    return {"id": wid, "message": "Warehouse created"}


@router.put("/warehouses/{warehouse_id}")
async def update_warehouse(warehouse_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM warehouses WHERE id = :id"), {"id": warehouse_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Warehouse not found")
    fields, params = [], {"id": warehouse_id}
    for col in ("name", "name_ar", "code", "address", "address_ar"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE warehouses SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Warehouse updated"}


@router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(warehouse_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM warehouses WHERE id = :id"), {"id": warehouse_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Warehouse not found")
    db.commit()
    return {"message": "Warehouse deleted"}


# ─── Stock Movements ─────────────────────────────

@router.get("/stock/movements")
async def list_stock_movements(
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if product_id:
        conditions.append("sm.product_id = :pid")
        params["pid"] = product_id
    if warehouse_id:
        conditions.append("sm.warehouse_id = :wid")
        params["wid"] = warehouse_id
    if movement_type:
        conditions.append("sm.movement_type = :mt")
        params["mt"] = movement_type
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM stock_movements sm WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT sm.id, sm.product_id, p.name, sm.warehouse_id, w.name, "
             f"sm.movement_type, sm.quantity, sm.unit_cost, sm.reference, sm.notes, "
             f"sm.movement_date, sm.created_at "
             f"FROM stock_movements sm "
             f"LEFT JOIN products p ON sm.product_id = p.id "
             f"LEFT JOIN warehouses w ON sm.warehouse_id = w.id "
             f"WHERE {where} ORDER BY sm.created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()

    data = [{"id": r[0], "product_id": r[1], "product_name": r[2],
             "warehouse_id": r[3], "warehouse_name": r[4],
             "movement_type": r[5], "quantity": r[6],
             "unit_cost": float(r[7]) if r[7] else 0,
             "reference": r[8], "notes": r[9],
             "movement_date": r[10].isoformat() if r[10] else None,
             "created_at": r[11].isoformat() if r[11] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/stock/movements", status_code=201)
async def create_stock_movement(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    mid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO stock_movements (id, product_id, warehouse_id, movement_type, "
             "quantity, unit_cost, reference, notes, movement_date, created_by, created_at) "
             "VALUES (:id, :pid, :wid, :mt, :qty, :uc, :ref, :notes, :md, :cb, :now)"),
        {"id": mid, "pid": body.get("product_id"), "wid": body.get("warehouse_id"),
         "mt": body.get("movement_type", "in"), "qty": body.get("quantity", 0),
         "uc": body.get("unit_cost", 0), "ref": body.get("reference"),
         "notes": body.get("notes"), "md": body.get("movement_date", now),
         "cb": user.get("id"), "now": now},
    )
    db.commit()
    return {"id": mid, "message": "Stock movement recorded"}


@router.get("/stock/product/{product_id}")
async def get_stock_by_product(product_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT sm.warehouse_id, w.name, SUM(sm.quantity) as total_qty "
             "FROM stock_movements sm LEFT JOIN warehouses w ON sm.warehouse_id = w.id "
             "WHERE sm.product_id = :pid GROUP BY sm.warehouse_id, w.name"),
        {"pid": product_id},
    ).fetchall()
    return [{"warehouse_id": r[0], "warehouse_name": r[1], "quantity": r[2]} for r in rows]


@router.get("/stock/alerts")
async def low_stock_alerts(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, sku, name, current_stock, min_stock FROM products "
             "WHERE is_active = true AND min_stock > 0 AND current_stock <= min_stock ORDER BY name")
    ).fetchall()
    return [{"id": r[0], "sku": r[1], "name": r[2], "current_stock": r[3], "min_stock": r[4]} for r in rows]


# ─── Categories ─────────────────────────────────

@router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT id, name, name_ar, description FROM products GROUP BY name, name_ar, description, id ORDER BY name")).fetchall()
        return [{"id": r[0], "name": r[1], "name_ar": r[2], "description": r[3]} for r in rows]
    except Exception:
        return []


# ─── Suppliers ─────────────────────────────────

@router.get("/suppliers")
async def list_suppliers(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if search:
        conditions.append("(name ILIKE :search OR code ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)
    count_row = db.execute(text(f"SELECT COUNT(*) FROM suppliers WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset
    rows = db.execute(
        text(f"SELECT id, tenant_id, name, name_ar, code, contact_person, email, phone, address, "
             f"tax_number, payment_terms, is_active, created_at "
             f"FROM suppliers WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "tenant_id": r[1], "name": r[2], "name_ar": r[3], "code": r[4],
             "contact_person": r[5], "email": r[6], "phone": r[7], "address": r[8],
             "tax_number": r[9], "payment_terms": r[10],
             "is_active": r[11] if r[11] is not None else True,
             "created_at": r[12].isoformat() if r[12] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/suppliers", status_code=201)
async def create_supplier(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO suppliers (id, tenant_id, name, name_ar, code, contact_person, email, phone, "
             "address, tax_number, payment_terms, is_active, created_at) "
             "VALUES (:id, :tid, :name, :name_ar, :code, :cp, :email, :phone, :addr, :tn, :pt, true, :now)"),
        {"id": sid, "tid": user.get("tenant_id"), "name": body.get("name", ""),
         "name_ar": body.get("name_ar"), "code": body.get("code", f"SUP-{sid[:6].upper()}"),
         "cp": body.get("contact_person"), "email": body.get("email"), "phone": body.get("phone"),
         "addr": body.get("address"), "tn": body.get("tax_number"),
         "pt": body.get("payment_terms"), "now": now},
    )
    db.commit()
    return {"id": sid, "message": "Supplier created"}


@router.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM suppliers WHERE id = :id"), {"id": supplier_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Supplier not found")
    fields, params = [], {"id": supplier_id}
    for col in ("name", "name_ar", "code", "contact_person", "email", "phone", "address", "tax_number", "payment_terms"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE suppliers SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Supplier updated"}


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM suppliers WHERE id = :id"), {"id": supplier_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Supplier not found")
    db.commit()
    return {"message": "Supplier deleted"}


# ─── Purchase Orders ─────────────────────────────

@router.get("/purchase-orders")
async def list_purchase_orders(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("po.status = :st")
        params["st"] = status
    if supplier_id:
        conditions.append("po.supplier_id = :sid")
        params["sid"] = supplier_id
    where = " AND ".join(conditions)
    count_row = db.execute(text(f"SELECT COUNT(*) FROM purchase_orders po WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset
    rows = db.execute(
        text(f"SELECT po.id, po.order_number, po.supplier_id, s.name, po.order_date, po.status, "
             f"po.total_amount, po.currency_code, po.created_at "
             f"FROM purchase_orders po LEFT JOIN suppliers s ON po.supplier_id = s.id "
             f"WHERE {where} ORDER BY po.created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "order_number": r[1], "supplier_id": r[2], "supplier_name": r[3],
             "order_date": r[4].isoformat() if r[4] else None, "status": r[5] or "draft",
             "total_amount": float(r[6]) if r[6] else 0, "currency_code": r[7] or "SAR",
             "created_at": r[8].isoformat() if r[8] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.post("/purchase-orders", status_code=201)
async def create_purchase_order(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    oid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO purchase_orders (id, tenant_id, company_id, order_number, supplier_id, "
             "order_date, status, total_amount, currency_code, created_at) "
             "VALUES (:id, :tid, :cid, :on, :sid, :od, 'draft', :amt, :cur, :now)"),
        {"id": oid, "tid": user.get("tenant_id"), "cid": user.get("tenant_id"),
         "on": f"PO-{oid[:8].upper()}", "sid": body.get("supplier_id"),
         "od": body.get("order_date", now), "amt": body.get("total_amount", 0),
         "cur": body.get("currency_code", "SAR"), "now": now},
    )
    db.commit()
    return {"id": oid, "message": "Purchase order created"}


@router.post("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(po_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = user.get("tenant_id")
    existing = db.execute(
        text("SELECT id, status, tenant_id FROM purchase_orders WHERE id = :id AND tenant_id = :tid"),
        {"id": po_id, "tid": tid},
    ).fetchone()
    if not existing:
        raise HTTPException(404, detail="Purchase order not found")
    if existing[1] == "received":
        return {"message": "Purchase order already received", "id": po_id}

    # Fixed H16: Receive stock for each PO line. Previously the endpoint
    # only flipped status and never updated inventory, so received goods
    # never appeared in stock levels.
    lines = db.execute(
        text("SELECT product_id, quantity, COALESCE(received_quantity,0) "
             "FROM purchase_order_lines WHERE purchase_order_id = :pid"),
        {"pid": po_id},
    ).fetchall()

    received_details = []
    for line in lines:
        product_id = line[0]
        qty = int(line[1] or 0)
        already_received = int(line[2] or 0)

        if product_id is None or qty <= 0:
            continue

        # Update the product's on-hand stock
        updated = db.execute(
            text("UPDATE products SET current_stock = current_stock + :q, "
                 "updated_at = :now WHERE id = :pid "
                 "RETURNING current_stock"),
            {"q": qty - already_received, "pid": product_id, "now": datetime.now(timezone.utc)},
        ).fetchone()
        if updated is None:
            raise HTTPException(404, detail=f"Product not found for line: {product_id}")

        # Mark the line as fully received
        db.execute(
            text("UPDATE purchase_order_lines SET received_quantity = :q "
                 "WHERE purchase_order_id = :pid AND product_id = :prod"),
            {"q": qty, "pid": po_id, "prod": product_id},
        )
        received_details.append({"product_id": product_id, "quantity": qty - already_received})

    db.execute(text("UPDATE purchase_orders SET status = 'received' WHERE id = :id"), {"id": po_id})
    db.commit()
    return {"message": "Purchase order received and stock updated", "id": po_id,
            "lines_received": received_details}
