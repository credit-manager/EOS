"""
P70.7 Restaurant ERP Professional — API
========================================
Built on Commerce Engine (items, stock, customers, suppliers) + Core (accounting, audit).
Restaurant-specific: Menu, Recipes, Tables, Reservations, Orders, KDS, Waste, Cash Drawer.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime, time

from database import SessionLocal, get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, get_company_id, check_permission,
    audit_log, post_journal,
    atomic_stock_receive, atomic_stock_issue,
    success_response, list_response, error_response,
    get_tenant_config,
)
from core.commerce_engine import (
    get_item as _ce_get_item,
    get_stock as _ce_get_stock,
    atomic_stock_receive as _ce_stock_receive,
    atomic_stock_issue as _ce_stock_issue,
)

router = APIRouter(prefix="/restaurant", tags=["Restaurant ERP"])


# ═══════════════════════════════════════════════════
# HELPERS (delegated to Commerce Engine)
# ═══════════════════════════════════════════════════

def _get_item(db, tenant_id, item_id):
    return _ce_get_item(db, tenant_id, item_id)


def _next_order_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_orders WHERE tenant_id=:t"),
                     {"t": tenant_id}).fetchone()
    return f"ORD-{(row[0] or 0) + 1:05d}"


def _next_waste_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_waste WHERE tenant_id=:t"),
                     {"t": tenant_id}).fetchone()
    return f"WST-{(row[0] or 0) + 1:04d}"


# ═══════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════

class SectionCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    sort_order: int = 0

class TableCreate(BaseModel):
    table_number: str
    section_id: Optional[str] = None
    capacity: int = 4
    x_pos: int = 0
    y_pos: int = 0

class ReservationCreate(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    table_id: Optional[str] = None
    reservation_date: str
    reservation_time: str
    party_size: int = 2
    notes: Optional[str] = None

class MenuCategoryCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None
    sort_order: int = 0
    icon: Optional[str] = None

class MenuItemCreate(BaseModel):
    item_code: str
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None
    category_id: Optional[str] = None
    commerce_item_id: Optional[str] = None
    selling_price: float = 0
    cost_price: float = 0
    prep_time_minutes: int = 0
    kitchen_station: Optional[str] = None
    tags: Optional[str] = None

class ModifierGroupCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    selection_type: str = "single"
    min_select: int = 0
    max_select: int = 1

class ModifierCreate(BaseModel):
    group_id: str
    name: str
    name_ar: Optional[str] = None
    price_adjustment: float = 0
    commerce_item_id: Optional[str] = None

class MenuItemModifierLink(BaseModel):
    menu_item_id: str
    modifier_group_id: str
    is_required: bool = False

class RecipeLineIn(BaseModel):
    commerce_item_id: str
    ingredient_name: Optional[str] = None
    qty: float = 1
    unit: str = "gram"
    unit_cost: float = 0
    waste_pct: float = 0

class RecipeCreate(BaseModel):
    menu_item_id: str
    recipe_name: Optional[str] = None
    yield_qty: float = 1
    yield_unit: str = "portion"
    prep_time_minutes: int = 0
    cook_time_minutes: int = 0
    instructions: Optional[str] = None
    lines: List[RecipeLineIn] = []

class ComboItemIn(BaseModel):
    menu_item_id: str
    qty: int = 1

class ComboCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    combo_price: float = 0
    items: List[ComboItemIn] = []

class OrderLineIn(BaseModel):
    menu_item_id: str
    qty: int = 1
    unit_price: float = 0
    discount_pct: float = 0
    modifier_ids: List[str] = []
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    order_type: str = "dine_in"
    table_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    waiter_id: Optional[str] = None
    guests_count: int = 1
    lines: List[OrderLineIn] = []
    notes: Optional[str] = None

class OrderLineStatusUpdate(BaseModel):
    status: str

class PaymentIn(BaseModel):
    payment_method: str = "cash"
    paid_amount: float = 0

class WasteItemIn(BaseModel):
    commerce_item_id: str
    item_name: Optional[str] = None
    qty: float = 1
    unit: str = "gram"
    unit_cost: float = 0
    reason: Optional[str] = None

class WasteCreate(BaseModel):
    waste_type: str = "production"
    reason: Optional[str] = None
    notes: Optional[str] = None
    items: List[WasteItemIn] = []

class CashDrawerOpen(BaseModel):
    opening_amount: float = 0

class CashDrawerClose(BaseModel):
    closing_amount: float = 0
    card_total: float = 0
    mobile_total: float = 0

class WaiterCreate(BaseModel):
    name: str
    employee_id: Optional[str] = None
    pin: Optional[str] = None
    section_id: Optional[str] = None

class ShiftCreate(BaseModel):
    shift_name: str
    start_time: str
    end_time: str

class ShiftAssignmentIn(BaseModel):
    waiter_id: str
    section_id: Optional[str] = None

class ShiftAssignmentCreate(BaseModel):
    shift_id: str
    assignment_date: str
    assignments: List[ShiftAssignmentIn] = []


# ═══════════════════════════════════════════════════
# 1. DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/dashboard")
def restaurant_dashboard(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    today = date.today().isoformat()

    orders = db.execute(text("SELECT COUNT(*),COALESCE(SUM(total),0) "
                            "FROM dbp_restaurant_orders WHERE tenant_id=:t "
                            "AND DATE(created_at)=:d AND status != 'voided'"),
                       {"t": t, "d": today}).fetchone()

    open_orders = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_orders "
                                 "WHERE tenant_id=:t AND status IN ('open','preparing','ready')"),
                            {"t": t}).fetchone()

    tables = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_tables "
                            "WHERE tenant_id=:t"), {"t": t}).fetchone()
    tables_occupied = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_tables "
                                     "WHERE tenant_id=:t AND status='occupied'"),
                                {"t": t}).fetchone()

    reservations = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_reservations "
                                  "WHERE tenant_id=:t AND reservation_date=:d "
                                  "AND status IN ('confirmed','checked_in')"),
                             {"t": t, "d": today}).fetchone()

    waste_cost = db.execute(text("SELECT COALESCE(SUM(total_cost),0) FROM dbp_restaurant_waste "
                                "WHERE tenant_id=:t AND waste_date=:d"),
                           {"t": t, "d": today}).fetchone()

    kitchen_pending = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_kitchen_orders "
                                     "WHERE tenant_id=:t AND status IN ('pending','firing','started')"),
                                {"t": t}).fetchone()

    return success_response("Restaurant dashboard", {
        "today": {
            "orders": orders[0] or 0,
            "revenue": float(orders[1] or 0),
            "open_orders": open_orders[0] or 0,
            "tables_total": tables[0] or 0,
            "tables_occupied": tables_occupied[0] or 0,
            "reservations": reservations[0] or 0,
            "waste_cost": float(waste_cost[0] or 0),
            "kitchen_pending": kitchen_pending[0] or 0,
        }
    })


# ═══════════════════════════════════════════════════
# 2. SECTIONS
# ═══════════════════════════════════════════════════

@router.post("/sections")
def create_section(body: SectionCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_sections (id,tenant_id,name,name_ar,sort_order) "
                   "VALUES (:id,:t,:n,:na,:so)"),
              {"id": sid, "t": t, "n": body.name, "na": body.name_ar, "so": body.sort_order})
    db.commit()
    return success_response("Section created", {"id": sid})


@router.get("/sections")
def list_sections(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,name_ar,sort_order,status "
                          "FROM dbp_restaurant_sections WHERE tenant_id=:t ORDER BY sort_order"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "name_ar": r[2], "sort_order": r[3], "status": r[4]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 3. TABLES
# ═══════════════════════════════════════════════════

@router.post("/tables")
def create_table(body: TableCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    tid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_tables "
                   "(id,tenant_id,table_number,section_id,capacity,x_pos,y_pos) "
                   "VALUES (:id,:t,:tn,:si,:c,:x,:y)"),
              {"id": tid, "t": t, "tn": body.table_number, "si": body.section_id,
               "c": body.capacity, "x": body.x_pos, "y": body.y_pos})
    db.commit()
    return success_response("Table created", {"id": tid})


@router.get("/tables")
def list_tables(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT rt.id,rt.table_number,rt.capacity,rt.status,rt.current_order_id,"
                          "rs.name,rt.section_id,rt.x_pos,rt.y_pos "
                          "FROM dbp_restaurant_tables rt "
                          "LEFT JOIN dbp_restaurant_sections rs ON rt.section_id=rs.id "
                          "WHERE rt.tenant_id=:t ORDER BY rt.table_number"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "table_number": r[1], "capacity": r[2], "status": r[3],
             "current_order_id": r[4], "section": r[5], "section_id": r[6],
             "x_pos": r[7], "y_pos": r[8]} for r in rows]
    return list_response(data, len(data))


@router.post("/tables/{table_id}/status")
def update_table_status(table_id: str, status: str = Query(...),
                       user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    valid = ["available", "occupied", "reserved", "cleaning"]
    if status not in valid:
        raise HTTPException(400, detail=f"Invalid status. Use: {valid}")
    old = db.execute(text("SELECT status FROM dbp_restaurant_tables WHERE id=:id AND tenant_id=:t"),
                    {"id": table_id, "t": t}).fetchone()
    db.execute(text("UPDATE dbp_restaurant_tables SET status=:s WHERE id=:id AND tenant_id=:t"),
              {"s": status, "id": table_id, "t": t})
    audit_log(db, t, user["id"], "update", "restaurant_table", table_id,
              old_values={"status": old[0] if old else None}, new_values={"status": status})
    db.commit()
    return success_response("Table status updated", {"id": table_id, "status": status})


# ═══════════════════════════════════════════════════
# 4. RESERVATIONS
# ═══════════════════════════════════════════════════

@router.post("/reservations")
def create_reservation(body: ReservationCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    rid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_reservations "
                   "(id,tenant_id,customer_name,customer_phone,customer_id,"
                   "table_id,reservation_date,reservation_time,party_size,notes) "
                   "VALUES (:id,:t,:cn,:cp,:ci,:ti,:rd,:rt,:ps,:n)"),
              {"id": rid, "t": t, "cn": body.customer_name, "cp": body.customer_phone,
               "ci": body.customer_id, "ti": body.table_id,
               "rd": body.reservation_date, "rt": body.reservation_time,
               "ps": body.party_size, "n": body.notes})
    if body.table_id:
        db.execute(text("UPDATE dbp_restaurant_tables SET status='reserved' "
                       "WHERE id=:id AND tenant_id=:t"), {"id": body.table_id, "t": t})
    audit_log(db, t, user["id"], "create", "reservation", rid,
              new_values={"customer": body.customer_name, "date": body.reservation_date})
    db.commit()
    return success_response("Reservation created", {"id": rid})


@router.get("/reservations")
def list_reservations(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    q = "SELECT id,customer_name,customer_phone,table_id,reservation_date," \
        "reservation_time,party_size,status,notes FROM dbp_restaurant_reservations " \
        "WHERE tenant_id=:t"
    params = {"t": t}
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY reservation_date, reservation_time"
    rows = db.execute(text(q), params).fetchall()
    data = [{"id": r[0], "customer_name": r[1], "phone": r[2], "table_id": r[3],
             "date": str(r[4]), "time": str(r[5]), "party_size": r[6],
             "status": r[7], "notes": r[8]} for r in rows]
    return list_response(data, len(data))


@router.post("/reservations/{res_id}/checkin")
def checkin_reservation(res_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    res = db.execute(text("SELECT id,table_id FROM dbp_restaurant_reservations "
                         "WHERE id=:id AND tenant_id=:t AND status='confirmed'"),
                    {"id": res_id, "t": t}).fetchone()
    if not res:
        raise HTTPException(404, detail="Reservation not found or not confirmed")
    db.execute(text("UPDATE dbp_restaurant_reservations SET status='checked_in', checked_in_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"), {"id": res_id, "t": t})
    if res[1]:
        db.execute(text("UPDATE dbp_restaurant_tables SET status='occupied' "
                       "WHERE id=:id AND tenant_id=:t"), {"id": res[1], "t": t})
    db.commit()
    return success_response("Guest checked in", {"id": res_id})


# ═══════════════════════════════════════════════════
# 5. MENU CATEGORIES
# ═══════════════════════════════════════════════════

@router.post("/menu/categories")
def create_menu_category(body: MenuCategoryCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    cid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_menu_categories "
                   "(id,tenant_id,name,name_ar,description,description_ar,sort_order,icon) "
                   "VALUES (:id,:t,:n,:na,:d,:da,:so,:ic)"),
              {"id": cid, "t": t, "n": body.name, "na": body.name_ar,
               "d": body.description, "da": body.description_ar,
               "so": body.sort_order, "ic": body.icon})
    db.commit()
    return success_response("Category created", {"id": cid})


@router.get("/menu/categories")
def list_menu_categories(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,name_ar,description,sort_order,icon,status "
                          "FROM dbp_restaurant_menu_categories WHERE tenant_id=:t ORDER BY sort_order"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "name_ar": r[2], "description": r[3],
             "sort_order": r[4], "icon": r[5], "status": r[6]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 6. MENU ITEMS
# ═══════════════════════════════════════════════════

@router.post("/menu/items")
def create_menu_item(body: MenuItemCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    mid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_menu_items "
                   "(id,tenant_id,item_code,name,name_ar,description,description_ar,"
                   "category_id,commerce_item_id,selling_price,cost_price,"
                   "prep_time_minutes,kitchen_station,tags) "
                   "VALUES (:id,:t,:ic,:n,:na,:d,:da,:ci,:mi,:sp,:cp,:pt,:ks,:tg)"),
              {"id": mid, "t": t, "ic": body.item_code, "n": body.name, "na": body.name_ar,
               "d": body.description, "da": body.description_ar,
               "ci": body.category_id, "mi": body.commerce_item_id,
               "sp": body.selling_price, "cp": body.cost_price,
               "pt": body.prep_time_minutes, "ks": body.kitchen_station, "tg": body.tags})
    db.commit()
    return success_response("Menu item created", {"id": mid})


@router.get("/menu/items")
def list_menu_items(category_id: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    q = "SELECT mi.id,mi.item_code,mi.name,mi.name_ar,mc.name,mi.selling_price," \
        "mi.cost_price,mi.is_available,mi.prep_time_minutes,mi.kitchen_station," \
        "mi.commerce_item_id,mi.category_id " \
        "FROM dbp_restaurant_menu_items mi " \
        "LEFT JOIN dbp_restaurant_menu_categories mc ON mi.category_id=mc.id " \
        "WHERE mi.tenant_id=:t"
    params = {"t": t}
    if category_id:
        q += " AND mi.category_id=:ci"
        params["ci"] = category_id
    q += " ORDER BY mi.sort_order, mi.name"
    rows = db.execute(text(q), params).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3],
             "category": r[4], "price": float(r[5] or 0), "cost": float(r[6] or 0),
             "available": r[7], "prep_time": r[8], "kitchen_station": r[9],
             "commerce_item_id": r[10], "category_id": r[11]} for r in rows]
    return list_response(data, len(data))


@router.put("/menu/items/{item_id}")
def update_menu_item(item_id: str, body: MenuItemCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    db.execute(text("UPDATE dbp_restaurant_menu_items SET "
                   "item_code=:ic,name=:n,name_ar=:na,description=:d,description_ar=:da,"
                   "category_id=:ci,commerce_item_id=:mi,selling_price=:sp,cost_price=:cp,"
                   "prep_time_minutes=:pt,kitchen_station=:ks,tags=:tg,updated_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"),
              {"id": item_id, "t": t, "ic": body.item_code, "n": body.name, "na": body.name_ar,
               "d": body.description, "da": body.description_ar,
               "ci": body.category_id, "mi": body.commerce_item_id,
               "sp": body.selling_price, "cp": body.cost_price,
               "pt": body.prep_time_minutes, "ks": body.kitchen_station, "tg": body.tags})
    db.commit()
    return success_response("Menu item updated", {"id": item_id})


@router.get("/menu/items/{item_id}")
def get_menu_item(item_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,item_code,name,name_ar,description,description_ar,"
                         "category_id,commerce_item_id,selling_price,cost_price,"
                         "prep_time_minutes,kitchen_station,tags,is_available "
                         "FROM dbp_restaurant_menu_items WHERE id=:id AND tenant_id=:t"),
                    {"id": item_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Menu item not found")
    return success_response("Menu item", {
        "id": row[0], "code": row[1], "name": row[2], "name_ar": row[3],
        "description": row[4], "description_ar": row[5],
        "category_id": row[6], "commerce_item_id": row[7],
        "price": float(row[8] or 0), "cost": float(row[9] or 0),
        "prep_time": row[10], "kitchen_station": row[11], "tags": row[12],
        "available": row[13]})


@router.post("/menu/items/{item_id}/availability")
def toggle_menu_item_availability(item_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    row = db.execute(text("SELECT is_available FROM dbp_restaurant_menu_items "
                         "WHERE id=:id AND tenant_id=:t"), {"id": item_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Menu item not found")
    new_val = not row[0]
    db.execute(text("UPDATE dbp_restaurant_menu_items SET is_available=:v "
                   "WHERE id=:id AND tenant_id=:t"),
              {"v": new_val, "id": item_id, "t": t})
    db.commit()
    return success_response("Availability toggled", {"id": item_id, "available": new_val})


# ═══════════════════════════════════════════════════
# 7. MODIFIER GROUPS & MODIFIERS
# ═══════════════════════════════════════════════════

@router.post("/menu/modifier-groups")
def create_modifier_group(body: ModifierGroupCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    gid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_modifier_groups "
                   "(id,tenant_id,name,name_ar,selection_type,min_select,max_select) "
                   "VALUES (:id,:t,:n,:na,:st,:mn,:mx)"),
              {"id": gid, "t": t, "n": body.name, "na": body.name_ar,
               "st": body.selection_type, "mn": body.min_select, "mx": body.max_select})
    db.commit()
    return success_response("Modifier group created", {"id": gid})


@router.get("/menu/modifier-groups")
def list_modifier_groups(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,name_ar,selection_type,min_select,max_select "
                          "FROM dbp_restaurant_modifier_groups WHERE tenant_id=:t ORDER BY name"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "name_ar": r[2], "selection_type": r[3],
             "min_select": r[4], "max_select": r[5]} for r in rows]
    return list_response(data, len(data))


@router.post("/menu/modifiers")
def create_modifier(body: ModifierCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    mid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_modifiers "
                   "(id,tenant_id,group_id,name,name_ar,price_adjustment,commerce_item_id) "
                   "VALUES (:id,:t,:gi,:n,:na,:pa,:mi)"),
              {"id": mid, "t": t, "gi": body.group_id, "n": body.name,
               "na": body.name_ar, "pa": body.price_adjustment, "mi": body.commerce_item_id})
    db.commit()
    return success_response("Modifier created", {"id": mid})


@router.post("/menu/item-modifiers")
def link_menu_item_modifier(body: MenuItemModifierLink, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    lid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_menu_modifiers "
                   "(id,tenant_id,menu_item_id,modifier_group_id,is_required) "
                   "VALUES (:id,:t,:mi,:gi,:ir)"),
              {"id": lid, "t": t, "mi": body.menu_item_id, "gi": body.modifier_group_id,
               "ir": body.is_required})
    db.commit()
    return success_response("Modifier linked to menu item", {"id": lid})


# ═══════════════════════════════════════════════════
# 8. COMBOS
# ═══════════════════════════════════════════════════

@router.post("/menu/combos")
def create_combo(body: ComboCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    cid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_combos "
                   "(id,tenant_id,name,name_ar,description,combo_price) "
                   "VALUES (:id,:t,:n,:na,:d,:cp)"),
              {"id": cid, "t": t, "n": body.name, "na": body.name_ar,
               "d": body.description, "cp": body.combo_price})
    for item in body.items:
        db.execute(text("INSERT INTO dbp_restaurant_combo_items "
                       "(id,tenant_id,combo_id,menu_item_id,qty) "
                       "VALUES (:id,:t,:ci,:mi,:q)"),
                  {"id": uid(), "t": t, "ci": cid, "mi": item.menu_item_id, "q": item.qty})
    db.commit()
    return success_response("Combo created", {"id": cid})


@router.get("/menu/combos")
def list_combos(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,name,name_ar,description,combo_price,is_active "
                          "FROM dbp_restaurant_combos WHERE tenant_id=:t ORDER BY name"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "name_ar": r[2], "description": r[3],
             "price": float(r[4] or 0), "active": r[5]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 9. RECIPES
# ═══════════════════════════════════════════════════

@router.post("/recipes")
def create_recipe(body: RecipeCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    rid = uid()
    total_cost = 0
    for line in body.lines:
        line_cost = line.qty * line.unit_cost
        if line.waste_pct > 0:
            line_cost *= (1 + line.waste_pct / 100)
        total_cost += line_cost
    cost_per_portion = total_cost / body.yield_qty if body.yield_qty > 0 else 0

    db.execute(text("INSERT INTO dbp_restaurant_recipes "
                   "(id,tenant_id,menu_item_id,recipe_name,yield_qty,yield_unit,"
                   "prep_time_minutes,cook_time_minutes,instructions,total_cost,cost_per_portion) "
                   "VALUES (:id,:t,:mi,:rn,:yq,:yu,:pt,:ct,:ins,:tc,:cpp)"),
              {"id": rid, "t": t, "mi": body.menu_item_id, "rn": body.recipe_name,
               "yq": body.yield_qty, "yu": body.yield_unit,
               "pt": body.prep_time_minutes, "ct": body.cook_time_minutes,
               "ins": body.instructions, "tc": total_cost, "cpp": cost_per_portion})
    for line in body.lines:
        line_cost = line.qty * line.unit_cost
        if line.waste_pct > 0:
            line_cost *= (1 + line.waste_pct / 100)
        db.execute(text("INSERT INTO dbp_restaurant_recipe_lines "
                       "(id,tenant_id,recipe_id,commerce_item_id,ingredient_name,"
                       "qty,unit,unit_cost,line_cost,waste_pct) "
                       "VALUES (:id,:t,:ri,:ci,:in,:q,:u,:uc,:lc,:wp)"),
                  {"id": uid(), "t": t, "ri": rid, "ci": line.commerce_item_id,
                   "in": line.ingredient_name, "q": line.qty, "u": line.unit,
                   "uc": line.unit_cost, "lc": line_cost, "wp": line.waste_pct})
    db.execute(text("UPDATE dbp_restaurant_menu_items SET cost_price=:cp WHERE id=:id AND tenant_id=:t"),
              {"cp": cost_per_portion, "id": body.menu_item_id, "t": t})
    db.commit()
    return success_response("Recipe created", {"id": rid, "total_cost": total_cost,
                                                "cost_per_portion": cost_per_portion})


@router.get("/recipes")
def list_recipes(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT r.id,r.recipe_name,mi.name,r.yield_qty,r.yield_unit,"
                          "r.total_cost,r.cost_per_portion,r.status "
                          "FROM dbp_restaurant_recipes r "
                          "LEFT JOIN dbp_restaurant_menu_items mi ON r.menu_item_id=mi.id "
                          "WHERE r.tenant_id=:t ORDER BY r.recipe_name"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "recipe_name": r[1], "menu_item": r[2],
             "yield_qty": r[3], "yield_unit": r[4],
             "total_cost": float(r[5] or 0), "cost_per_portion": float(r[6] or 0),
             "status": r[7]} for r in rows]
    return list_response(data, len(data))


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT r.id,r.recipe_name,r.menu_item_id,mi.name,r.yield_qty,r.yield_unit,"
                         "r.prep_time_minutes,r.cook_time_minutes,r.instructions,"
                         "r.total_cost,r.cost_per_portion "
                         "FROM dbp_restaurant_recipes r "
                         "LEFT JOIN dbp_restaurant_menu_items mi ON r.menu_item_id=mi.id "
                         "WHERE r.id=:id AND r.tenant_id=:t"),
                    {"id": recipe_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Recipe not found")
    lines = db.execute(text("SELECT rl.commerce_item_id,ti.name,rl.qty,rl.unit,"
                           "rl.unit_cost,rl.line_cost,rl.waste_pct "
                           "FROM dbp_restaurant_recipe_lines rl "
                           "LEFT JOIN dbp_commerce_items ti ON rl.commerce_item_id=ti.id "
                           "WHERE rl.recipe_id=:rid"),
                      {"rid": recipe_id}).fetchall()
    return success_response("Recipe", {
        "id": row[0], "recipe_name": row[1], "menu_item_id": row[2], "menu_item": row[3],
        "yield_qty": row[4], "yield_unit": row[5],
        "prep_time": row[6], "cook_time": row[7], "instructions": row[8],
        "total_cost": float(row[9] or 0), "cost_per_portion": float(row[10] or 0),
        "lines": [{"item_id": l[0], "item_name": l[1], "qty": float(l[2]),
                   "unit": l[3], "unit_cost": float(l[4]),
                   "line_cost": float(l[5]), "waste_pct": float(l[6])} for l in lines]
    })


# ═══════════════════════════════════════════════════
# 10. ORDERS
# ═══════════════════════════════════════════════════

@router.post("/orders")
def create_order(body: OrderCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_types = ["dine_in", "takeaway", "delivery"]
    if body.order_type not in valid_types:
        raise HTTPException(400, detail=f"Invalid order type: {body.order_type}. Use: {valid_types}")
    if not body.lines:
        raise HTTPException(400, detail="Order must have at least one item")
    for l in body.lines:
        if l.qty <= 0:
            raise HTTPException(400, detail=f"Invalid qty: {l.qty}")
        if l.unit_price < 0:
            raise HTTPException(400, detail=f"Invalid price: {l.unit_price}")
    oid = uid()
    order_num = _next_order_number(db, t)
    subtotal = 0
    total_cost = 0

    for l in body.lines:
        line_total = l.unit_price * l.qty
        if l.discount_pct > 0:
            line_total -= line_total * l.discount_pct / 100
        subtotal += line_total

    # Fixed H12: VAT rate is now configurable per tenant (default 15%).
    tax_rate = float(get_tenant_config(db, t, "vat_rate", 15.0))
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax

    db.execute(text("INSERT INTO dbp_restaurant_orders "
                   "(id,tenant_id,order_number,order_type,table_id,customer_id,"
                   "customer_name,waiter_id,subtotal,tax_amount,total,guests_count,notes) "
                   "VALUES (:id,:t,:on,:ot,:ti,:ci,:cn,:wi,:st,:tx,:tot,:gc,:n)"),
              {"id": oid, "t": t, "on": order_num, "ot": body.order_type,
               "ti": body.table_id, "ci": body.customer_id, "cn": body.customer_name,
               "wi": body.waiter_id, "st": subtotal, "tx": tax, "tot": total,
               "gc": body.guests_count, "n": body.notes})

    for l in body.lines:
        lid = uid()
        line_total = l.unit_price * l.qty
        if l.discount_pct > 0:
            line_total -= line_total * l.discount_pct / 100
        db.execute(text("INSERT INTO dbp_restaurant_order_lines "
                       "(id,tenant_id,order_id,menu_item_id,item_name,qty,"
                       "unit_price,discount_pct,line_total,notes) "
                       "VALUES (:id,:t,:oi,:mi,:in,:q,:up,:dd,:lt,:n)"),
                  {"id": lid, "t": t, "oi": oid, "mi": l.menu_item_id,
                   "in": _get_menu_item_name(db, t, l.menu_item_id),
                   "q": l.qty, "up": l.unit_price, "dd": l.discount_pct,
                   "lt": line_total, "n": l.notes})
        for mid in l.modifier_ids:
            mod = db.execute(text("SELECT id,name,price_adjustment FROM dbp_restaurant_modifiers "
                                 "WHERE id=:id AND tenant_id=:t"), {"id": mid, "t": t}).fetchone()
            if mod:
                db.execute(text("INSERT INTO dbp_restaurant_order_modifiers "
                               "(id,tenant_id,order_line_id,modifier_id,modifier_name,price_adjustment) "
                               "VALUES (:id,:t,:oli,:mi,:mn,:pa)"),
                          {"id": uid(), "t": t, "oli": lid, "mi": mod[0],
                           "mn": mod[1], "pa": float(mod[2] or 0)})

    if body.table_id:
        db.execute(text("UPDATE dbp_restaurant_tables SET status='occupied',current_order_id=:oid "
                       "WHERE id=:id AND tenant_id=:t"),
                  {"oid": oid, "id": body.table_id, "t": t})

    audit_log(db, t, user["id"], "create", "restaurant_order", oid,
              new_values={"order_number": order_num, "type": body.order_type, "total": total})
    db.commit()
    return success_response("Order created", {"id": oid, "order_number": order_num, "total": total})


def _get_menu_item_name(db, tenant_id, item_id):
    row = db.execute(text("SELECT name FROM dbp_restaurant_menu_items WHERE id=:id AND tenant_id=:t"),
                    {"id": item_id, "t": tenant_id}).fetchone()
    return row[0] if row else "Unknown"


@router.get("/orders")
def list_orders(status: Optional[str] = None, order_type: Optional[str] = None,
               user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    q = "SELECT o.id,o.order_number,o.order_type,o.table_id,o.customer_name," \
        "o.subtotal,o.tax_amount,o.total,o.status,o.kitchen_status," \
        "o.payment_method,o.guests_count,o.created_at " \
        "FROM dbp_restaurant_orders o WHERE o.tenant_id=:t AND o.status != 'voided'"
    params = {"t": t}
    if status:
        q += " AND o.status=:s"
        params["s"] = status
    if order_type:
        q += " AND o.order_type=:ot"
        params["ot"] = order_type
    q += " ORDER BY o.created_at DESC LIMIT 100"
    rows = db.execute(text(q), params).fetchall()
    data = [{"id": r[0], "order_number": r[1], "type": r[2], "table_id": r[3],
             "customer": r[4], "subtotal": float(r[5] or 0), "tax": float(r[6] or 0),
             "total": float(r[7] or 0), "status": r[8], "kitchen_status": r[9],
             "payment": r[10], "guests": r[11], "created": str(r[12])} for r in rows]
    return list_response(data, len(data))


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    row = db.execute(text("SELECT id,order_number,order_type,table_id,customer_id,customer_name,"
                         "waiter_id,subtotal,tax_amount,discount_amount,total,paid_amount,"
                         "change_amount,payment_method,status,kitchen_status,notes,"
                         "guests_count,created_at "
                         "FROM dbp_restaurant_orders WHERE id=:id AND tenant_id=:t"),
                    {"id": order_id, "t": t}).fetchone()
    if not row:
        raise HTTPException(404, detail="Order not found")
    lines = db.execute(text("SELECT ol.id,ol.menu_item_id,ol.item_name,ol.qty,"
                           "ol.unit_price,ol.discount_pct,ol.discount_amount,"
                           "ol.line_total,ol.status,ol.notes "
                           "FROM dbp_restaurant_order_lines ol "
                           "WHERE ol.order_id=:oid"),
                      {"oid": order_id}).fetchall()
    line_data = []
    for l in lines:
        mods = db.execute(text("SELECT modifier_name,price_adjustment "
                              "FROM dbp_restaurant_order_modifiers WHERE order_line_id=:lid"),
                         {"lid": l[0]}).fetchall()
        line_data.append({"id": l[0], "menu_item_id": l[1], "name": l[2],
                          "qty": l[3], "price": float(l[4] or 0),
                          "discount_pct": float(l[5] or 0),
                          "discount_amount": float(l[6] or 0),
                          "line_total": float(l[7] or 0),
                          "status": l[8], "notes": l[9],
                          "modifiers": [{"name": m[0], "adjustment": float(m[1] or 0)} for m in mods]})
    return success_response("Order", {
        "id": row[0], "order_number": row[1], "type": row[2], "table_id": row[3],
        "customer_id": row[4], "customer_name": row[5], "waiter_id": row[6],
        "subtotal": float(row[7] or 0), "tax": float(row[8] or 0),
        "discount": float(row[9] or 0), "total": float(row[10] or 0),
        "paid": float(row[11] or 0), "change": float(row[12] or 0),
        "payment": row[13], "status": row[14], "kitchen_status": row[15],
        "notes": row[16], "guests": row[17], "created": str(row[18]),
        "lines": line_data})


@router.post("/orders/{order_id}/send-to-kitchen")
def send_to_kitchen(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    order = db.execute(text("SELECT id,table_id FROM dbp_restaurant_orders "
                           "WHERE id=:id AND tenant_id=:t AND status='open'"),
                      {"id": order_id, "t": t}).fetchone()
    if not order:
        raise HTTPException(404, detail="Open order not found")
    lines = db.execute(text("SELECT id,menu_item_id,qty,notes "
                          "FROM dbp_restaurant_order_lines "
                          "WHERE order_id=:oid AND status='pending'"),
                     {"oid": order_id}).fetchall()
    for l in lines:
        mi = db.execute(text("SELECT kitchen_station FROM dbp_restaurant_menu_items "
                            "WHERE id=:id AND tenant_id=:t"),
                       {"id": l[1], "t": t}).fetchone()
        station = mi[0] if mi and mi[0] else "general"
        st_row = db.execute(text("SELECT id FROM dbp_restaurant_kitchen_stations "
                                "WHERE UPPER(station_code)=UPPER(:sc) AND tenant_id=:t"),
                           {"sc": station, "t": t}).fetchone()
        if st_row:
            db.execute(text("INSERT INTO dbp_restaurant_kitchen_orders "
                           "(id,tenant_id,order_id,order_line_id,station_id,status,fired_at) "
                           "VALUES (:id,:t,:oi,:li,:si,'fired',NOW())"),
                      {"id": uid(), "t": t, "oi": order_id, "li": l[0], "si": st_row[0]})
        db.execute(text("UPDATE dbp_restaurant_order_lines SET status='fired',sent_to_kitchen_at=NOW() "
                       "WHERE id=:id AND tenant_id=:t"), {"id": l[0], "t": t})
    db.execute(text("UPDATE dbp_restaurant_orders SET kitchen_status='fired' "
                   "WHERE id=:id AND tenant_id=:t"), {"id": order_id, "t": t})
    db.commit()
    return success_response("Sent to kitchen", {"id": order_id, "items_sent": len(lines)})


@router.post("/orders/{order_id}/pay")
def pay_order(order_id: str, body: PaymentIn, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_payments = ["cash", "card", "mobile"]
    if body.payment_method not in valid_payments:
        raise HTTPException(400, detail=f"Invalid payment method: {body.payment_method}. Use: {valid_payments}")
    order = db.execute(text("SELECT id,total,status,table_id,order_number "
                           "FROM dbp_restaurant_orders WHERE id=:id AND tenant_id=:t"),
                      {"id": order_id, "t": t}).fetchone()
    if not order:
        raise HTTPException(404, detail="Order not found")
    if order[2] == "paid":
        raise HTTPException(400, detail="Already paid")
    total = float(order[1])
    paid = body.paid_amount
    if paid < total:
        raise HTTPException(400, detail=f"Paid {paid} < total {total}")
    change = paid - total

    db.execute(text("UPDATE dbp_restaurant_orders SET status='paid',payment_method=:pm,"
                   "paid_amount=:pa,change_amount=:ca,completed_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"),
              {"pm": body.payment_method, "pa": paid, "ca": change, "id": order_id, "t": t})
    if order[3]:
        db.execute(text("UPDATE dbp_restaurant_tables SET status='cleaning',current_order_id=NULL "
                       "WHERE id=:id AND tenant_id=:t"), {"id": order[3], "t": t})

    company_id = get_company_id(db, t)
    post_journal(db, t, company_id, "restaurant_sale", f"Restaurant Sale {order[4]}",
                 [{"account_code": "1000", "description": "Cash", "debit": total},
                  {"account_code": "4000", "description": "Revenue", "credit": total}])

    audit_log(db, t, user["id"], "pay", "restaurant_order", order_id,
              new_values={"paid": paid, "method": body.payment_method})
    db.commit()
    return success_response("Order paid", {"id": order_id, "change": change})


@router.post("/orders/{order_id}/void")
def void_order(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    order = db.execute(text("SELECT id,total,status,table_id,order_number "
                           "FROM dbp_restaurant_orders WHERE id=:id AND tenant_id=:t"),
                      {"id": order_id, "t": t}).fetchone()
    if not order:
        raise HTTPException(404, detail="Order not found")
    if order[2] == "voided":
        raise HTTPException(400, detail="Already voided")
    db.execute(text("UPDATE dbp_restaurant_orders SET status='voided' "
                   "WHERE id=:id AND tenant_id=:t"), {"id": order_id, "t": t})
    if order[3]:
        db.execute(text("UPDATE dbp_restaurant_tables SET status='available',current_order_id=NULL "
                       "WHERE id=:id AND tenant_id=:t"), {"id": order[3], "t": t})
    company_id = get_company_id(db, t)
    total = float(order[1])
    post_journal(db, t, company_id, "restaurant_void", f"Void {order[4]}",
                 [{"account_code": "4000", "description": "Revenue", "debit": total},
                  {"account_code": "1000", "description": "Cash", "credit": total}])
    audit_log(db, t, user["id"], "void", "restaurant_order", order_id,
              old_values={"total": total}, new_values={"status": "voided"})
    db.commit()
    return success_response("Order voided", {"id": order_id})


# ═══════════════════════════════════════════════════
# 11. KITCHEN DISPLAY (KDS)
# ═══════════════════════════════════════════════════

@router.get("/kitchen/orders")
def kitchen_orders(station_id: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    q = "SELECT ko.id,o.order_number,ol.item_name,ol.qty,ko.status," \
        "ko.priority,ko.fired_at,ko.started_at,ko.eta_minutes,r.table_number " \
        "FROM dbp_restaurant_kitchen_orders ko " \
        "JOIN dbp_restaurant_orders o ON ko.order_id=o.id " \
        "JOIN dbp_restaurant_order_lines ol ON ko.order_line_id=ol.id " \
        "LEFT JOIN dbp_restaurant_tables r ON o.table_id=r.id " \
        "WHERE ko.tenant_id=:t AND ko.status IN ('pending','fired','started')"
    params = {"t": t}
    if station_id:
        q += " AND ko.station_id=:si"
        params["si"] = station_id
    q += " ORDER BY ko.priority DESC, ko.fired_at ASC"
    rows = db.execute(text(q), params).fetchall()
    data = [{"id": r[0], "order_number": r[1], "item": r[2], "qty": r[3],
             "status": r[4], "priority": r[5], "fired_at": str(r[6]),
             "started_at": str(r[7]) if r[7] else None,
             "eta": r[8], "table": r[9]} for r in rows]
    return list_response(data, len(data))


@router.post("/kitchen/orders/{ko_id}/start")
def start_kitchen_order(ko_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    db.execute(text("UPDATE dbp_restaurant_kitchen_orders SET status='started',started_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t AND status IN ('pending','fired')"),
              {"id": ko_id, "t": t})
    audit_log(db, t, user["id"], "start", "kitchen_order", ko_id,
              new_values={"status": "started"})
    db.commit()
    return success_response("Kitchen order started", {"id": ko_id})


@router.post("/kitchen/orders/{ko_id}/complete")
def complete_kitchen_order(ko_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    ko = db.execute(text("SELECT id,order_id,order_line_id FROM dbp_restaurant_kitchen_orders "
                        "WHERE id=:id AND tenant_id=:t"),
                   {"id": ko_id, "t": t}).fetchone()
    if not ko:
        raise HTTPException(404, detail="Kitchen order not found")
    db.execute(text("UPDATE dbp_restaurant_kitchen_orders SET status='done',completed_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"), {"id": ko_id, "t": t})
    db.execute(text("UPDATE dbp_restaurant_order_lines SET status='prepared',prepared_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"), {"id": ko[2], "t": t})
    remaining = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_kitchen_orders "
                               "WHERE order_id=:oid AND status != 'done'"),
                          {"oid": ko[1]}).fetchone()
    if remaining[0] == 0:
        db.execute(text("UPDATE dbp_restaurant_orders SET kitchen_status='ready' "
                       "WHERE id=:id AND tenant_id=:t"), {"id": ko[1], "t": t})
    audit_log(db, t, user["id"], "complete", "kitchen_order", ko_id,
              new_values={"status": "done"})
    db.commit()
    return success_response("Kitchen order completed", {"id": ko_id})


@router.get("/kitchen/stations")
def list_kitchen_stations(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,station_code,name,name_ar,station_type,status "
                          "FROM dbp_restaurant_kitchen_stations WHERE tenant_id=:t"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3],
             "type": r[4], "status": r[5]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 12. WASTE
# ═══════════════════════════════════════════════════

@router.post("/waste")
def create_waste(body: WasteCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    if not body.items:
        raise HTTPException(400, detail="Waste must have at least one item")
    for item in body.items:
        if item.qty <= 0:
            raise HTTPException(400, detail=f"Invalid waste qty: {item.qty}")
    wid = uid()
    waste_num = _next_waste_number(db, t)
    total_cost = sum(i.qty * i.unit_cost for i in body.items)
    db.execute(text("INSERT INTO dbp_restaurant_waste "
                   "(id,tenant_id,waste_number,waste_date,waste_type,reason,total_cost,reported_by,notes) "
                   "VALUES (:id,:t,:wn,CURRENT_DATE,:wt,:r,:tc,:rb,:n)"),
              {"id": wid, "t": t, "wn": waste_num, "wt": body.waste_type,
               "r": body.reason, "tc": total_cost, "rb": user["id"], "n": body.notes})
    for item in body.items:
        item_cost = item.qty * item.unit_cost
        db.execute(text("INSERT INTO dbp_restaurant_waste_items "
                       "(id,tenant_id,waste_id,commerce_item_id,item_name,qty,unit,unit_cost,total_cost,reason) "
                       "VALUES (:id,:t,:wi,:ci,:in,:q,:u,:uc,:tc,:r)"),
                  {"id": uid(), "t": t, "wi": wid, "ci": item.commerce_item_id,
                   "in": item.item_name, "q": item.qty, "u": item.unit,
                   "uc": item.unit_cost, "tc": item_cost, "r": item.reason})
    company_id = get_company_id(db, t)
    if total_cost > 0:
        post_journal(db, t, company_id, "restaurant_waste", f"Waste {waste_num}",
                     [{"account_code": "5200", "description": "Waste Expense", "debit": total_cost},
                      {"account_code": "1300", "description": "Inventory", "credit": total_cost}])
    audit_log(db, t, user["id"], "create", "waste", wid,
              new_values={"number": waste_num, "cost": total_cost})
    db.commit()
    return success_response("Waste recorded", {"id": wid, "number": waste_num, "total_cost": total_cost})


@router.get("/waste")
def list_waste(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,waste_number,waste_date,waste_type,reason,total_cost,status "
                          "FROM dbp_restaurant_waste WHERE tenant_id=:t ORDER BY waste_date DESC"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "number": r[1], "date": str(r[2]), "type": r[3],
             "reason": r[4], "total_cost": float(r[5] or 0), "status": r[6]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 13. CASH DRAWER
# ═══════════════════════════════════════════════════

@router.post("/cash-drawer/open")
def open_cash_drawer(body: CashDrawerOpen, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    today = date.today().isoformat()
    existing = db.execute(text("SELECT id FROM dbp_restaurant_cash_drawer "
                              "WHERE tenant_id=:t AND drawer_date=:d AND status='open'"),
                         {"t": t, "d": today}).fetchone()
    if existing:
        raise HTTPException(400, detail="Cash drawer already open for today")
    cid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_cash_drawer "
                   "(id,tenant_id,drawer_date,opening_amount,opened_by) "
                   "VALUES (:id,:t,:da,:oa,:ob)"),
              {"id": cid, "t": t, "da": today, "oa": body.opening_amount, "ob": user["id"]})
    db.commit()
    return success_response("Cash drawer opened", {"id": cid})


@router.post("/cash-drawer/close")
def close_cash_drawer(body: CashDrawerClose, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "approve")
    t = user["tenant_id"]
    today = date.today().isoformat()
    drawer = db.execute(text("SELECT id,opening_amount FROM dbp_restaurant_cash_drawer "
                            "WHERE tenant_id=:t AND drawer_date=:d AND status='open'"),
                       {"t": t, "d": today}).fetchone()
    if not drawer:
        raise HTTPException(404, detail="No open cash drawer for today")
    opening = float(drawer[1] or 0)
    day_orders = db.execute(text("SELECT COALESCE(SUM(paid_amount),0) FROM dbp_restaurant_orders "
                                "WHERE tenant_id=:t AND DATE(created_at)=:d "
                                "AND status='paid' AND payment_method='cash'"),
                           {"t": t, "d": today}).fetchone()
    cash_sales = float(day_orders[0] or 0)
    expected = opening + cash_sales
    variance = body.closing_amount - expected
    db.execute(text("UPDATE dbp_restaurant_cash_drawer SET "
                   "closing_amount=:ca,card_total=:ct,mobile_total=:mt,"
                   "expected_cash=:ec,actual_cash=:ac,variance=:v,"
                   "status='closed',closed_by=:cb,closed_at=NOW() "
                   "WHERE id=:id AND tenant_id=:t"),
              {"ca": body.closing_amount, "ct": body.card_total, "mt": body.mobile_total,
               "ec": expected, "ac": body.closing_amount, "v": variance,
               "cb": user["id"], "id": drawer[0], "t": t})
    db.commit()
    return success_response("Cash drawer closed", {"id": drawer[0], "variance": variance})


@router.get("/cash-drawer")
def get_cash_drawer(date_filter: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    q = "SELECT id,drawer_date,opening_amount,closing_amount,expected_cash," \
        "actual_cash,variance,status FROM dbp_restaurant_cash_drawer " \
        "WHERE tenant_id=:t"
    params = {"t": t}
    if date_filter:
        q += " AND drawer_date=:d"
        params["d"] = date_filter
    q += " ORDER BY drawer_date DESC LIMIT 30"
    rows = db.execute(text(q), params).fetchall()
    data = [{"id": r[0], "date": str(r[1]), "opening": float(r[2] or 0),
             "closing": float(r[3] or 0) if r[3] else None,
             "expected": float(r[4] or 0) if r[4] else None,
             "actual": float(r[5] or 0) if r[5] else None,
             "variance": float(r[6] or 0) if r[6] else None,
             "status": r[7]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 14. WAITERS
# ═══════════════════════════════════════════════════

@router.post("/waiters")
def create_waiter(body: WaiterCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    wid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_waiters "
                   "(id,tenant_id,employee_id,name,pin,section_id) "
                   "VALUES (:id,:t,:ei,:n,:pi,:si)"),
              {"id": wid, "t": t, "ei": body.employee_id, "n": body.name,
               "pi": body.pin, "si": body.section_id})
    db.commit()
    return success_response("Waiter created", {"id": wid})


@router.get("/waiters")
def list_waiters(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT w.id,w.name,w.status,rs.name "
                          "FROM dbp_restaurant_waiters w "
                          "LEFT JOIN dbp_restaurant_sections rs ON w.section_id=rs.id "
                          "WHERE w.tenant_id=:t ORDER BY w.name"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "status": r[2], "section": r[3]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# 15. SHIFTS
# ═══════════════════════════════════════════════════

@router.post("/shifts")
def create_shift(body: ShiftCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sid = uid()
    db.execute(text("INSERT INTO dbp_restaurant_shifts "
                   "(id,tenant_id,shift_name,start_time,end_time) "
                   "VALUES (:id,:t,:sn,:st,:et)"),
              {"id": sid, "t": t, "sn": body.shift_name, "st": body.start_time, "et": body.end_time})
    db.commit()
    return success_response("Shift created", {"id": sid})


@router.get("/shifts")
def list_shifts(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,shift_name,start_time,end_time,status "
                          "FROM dbp_restaurant_shifts WHERE tenant_id=:t ORDER BY start_time"),
                     {"t": t}).fetchall()
    data = [{"id": r[0], "name": r[1], "start": str(r[2]), "end": str(r[3]),
             "status": r[4]} for r in rows]
    return list_response(data, len(data))


@router.post("/shifts/assign")
def assign_shift(body: ShiftAssignmentCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    count = 0
    for a in body.assignments:
        aid = uid()
        db.execute(text("INSERT INTO dbp_restaurant_shift_assignments "
                       "(id,tenant_id,shift_id,waiter_id,assignment_date,section_id) "
                       "VALUES (:id,:t,:si,:wi,:ad,:sci)"),
                  {"id": aid, "t": t, "si": body.shift_id, "wi": a.waiter_id,
                   "ad": body.assignment_date, "sci": a.section_id})
        count += 1
    db.commit()
    return success_response("Shift assignments created", {"count": count})


# ═══════════════════════════════════════════════════
# 16. ANALYTICS
# ═══════════════════════════════════════════════════

@router.get("/analytics/popular-items")
def popular_items(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT ol.item_name,SUM(ol.qty) as total_qty,"
                          "SUM(ol.line_total) as total_revenue "
                          "FROM dbp_restaurant_order_lines ol "
                          "JOIN dbp_restaurant_orders o ON ol.order_id=o.id "
                          "WHERE o.tenant_id=:t AND o.status != 'voided' "
                          "GROUP BY ol.item_name ORDER BY total_qty DESC LIMIT 10"),
                     {"t": t}).fetchall()
    data = [{"name": r[0], "qty_sold": int(r[1] or 0),
             "revenue": float(r[2] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/analytics/revenue-by-type")
def revenue_by_type(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT order_type,COUNT(*),SUM(total) "
                          "FROM dbp_restaurant_orders "
                          "WHERE tenant_id=:t AND status != 'voided' "
                          "GROUP BY order_type"),
                     {"t": t}).fetchall()
    data = [{"type": r[0], "orders": int(r[1] or 0),
             "revenue": float(r[2] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/analytics/food-cost")
def food_cost_analytics(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT mi.name,r.total_cost,r.cost_per_portion,"
                          "mi.selling_price,"
                          "CASE WHEN mi.selling_price > 0 "
                          "THEN ROUND(r.cost_per_portion / mi.selling_price * 100, 1) ELSE 0 END as food_cost_pct "
                          "FROM dbp_restaurant_recipes r "
                          "JOIN dbp_restaurant_menu_items mi ON r.menu_item_id=mi.id "
                          "WHERE r.tenant_id=:t AND r.status='active' "
                          "ORDER BY food_cost_pct DESC LIMIT 10"),
                     {"t": t}).fetchall()
    data = [{"menu_item": r[0], "recipe_cost": float(r[1] or 0),
             "cost_per_portion": float(r[2] or 0), "selling_price": float(r[3] or 0),
             "food_cost_pct": float(r[4] or 0)} for r in rows]
    return list_response(data, len(data))


@router.get("/analytics/table-turnover")
def table_turnover(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT rt.table_number,COUNT(o.id) as orders,"
                          "AVG(EXTRACT(EPOCH FROM (o.completed_at - o.opened_at))/60) as avg_minutes "
                          "FROM dbp_restaurant_tables rt "
                          "LEFT JOIN dbp_restaurant_orders o ON rt.id=o.table_id "
                          "AND o.status='paid' AND o.completed_at > NOW() - INTERVAL '7 days' "
                          "WHERE rt.tenant_id=:t "
                          "GROUP BY rt.table_number ORDER BY orders DESC"),
                     {"t": t}).fetchall()
    data = [{"table": r[0], "orders_7d": int(r[1] or 0),
             "avg_duration_min": round(float(r[2] or 0), 1)} for r in rows]
    return list_response(data, len(data))
