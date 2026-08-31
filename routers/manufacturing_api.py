"""
P70.8.2 Manufacturing ERP Professional — API
=============================================
35+ endpoints: BOM, Work Centers, Routings, Production Orders,
Material Issues, Receipts, Quality, Scrap, Costs, Dashboard.
All items/stock via Commerce Engine. Accounting via Core.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

from database import SessionLocal, get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, get_company_id, check_permission,
    audit_log, post_journal,
    atomic_stock_receive, atomic_stock_issue,
    success_response, list_response, error_response,
)
from core.commerce_engine import (
    get_item as _ce_get_item,
    get_stock as _ce_get_stock,
)

router = APIRouter(prefix="/manufacturing", tags=["Manufacturing ERP"])


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

VALID_ORDER_STATUSES = {"planned", "released", "in_progress", "completed", "cancelled"}
VALID_BOM_STATUSES = {"draft", "active", "inactive", "archived"}
VALID_WC_TYPES = {"machine", "labor", "both"}
VALID_WC_STATUSES = {"active", "inactive", "maintenance"}
VALID_ROUTING_STATUSES = {"draft", "active", "inactive"}
VALID_MI_STATUSES = {"pending", "partial", "completed", "cancelled"}
VALID_QI_TYPES = {"incoming", "in_process", "final", "random"}
VALID_QI_RESULTS = {"pending", "passed", "failed", "partial"}
VALID_COST_TYPES = {"material", "labor", "overhead", "setup", "scrap", "other"}

def _validate_order_status(status):
    if status not in VALID_ORDER_STATUSES:
        raise HTTPException(400, detail=f"Invalid order status: {status}")

def _validate_bom_status(status):
    if status not in VALID_BOM_STATUSES:
        raise HTTPException(400, detail=f"Invalid BOM status: {status}")

def _get_item(db, tenant_id, item_id):
    return _ce_get_item(db, tenant_id, item_id)

def _next_order_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": tenant_id}).fetchone()
    n = (row[0] or 0) + 1
    return f"MO-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

def _next_issue_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_material_issues WHERE tenant_id=:t"), {"t": tenant_id}).fetchone()
    n = (row[0] or 0) + 1
    return f"MI-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

def _next_receipt_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_receipts WHERE tenant_id=:t"), {"t": tenant_id}).fetchone()
    n = (row[0] or 0) + 1
    return f"MFR-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

def _next_inspection_number(db, tenant_id):
    row = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_quality_inspections WHERE tenant_id=:t"), {"t": tenant_id}).fetchone()
    n = (row[0] or 0) + 1
    return f"QI-{datetime.now().strftime('%Y%m%d')}-{n:04d}"


# ═══════════════════════════════════════════════════
# BOM (Bill of Materials)
# ═══════════════════════════════════════════════════

class BOMLineCreate(BaseModel):
    item_id: str
    qty: float = Field(ge=0.01)
    unit: str = "piece"
    scrap_pct: float = Field(default=0, ge=0, le=100)
    cost_estimate: float = Field(default=0, ge=0)
    sort_order: int = 0
    notes: Optional[str] = None

class BOMCreate(BaseModel):
    bom_code: str
    name: str
    item_id: str
    revision: str = "A"
    description: Optional[str] = None
    lines: List[BOMLineCreate] = []

@router.post("/bom")
def create_bom(body: BOMCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_mfg_bom WHERE tenant_id=:t AND bom_code=:c"),
                          {"t": t, "c": body.bom_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="BOM code already exists")
    bid = uid()
    db.execute(text("INSERT INTO dbp_mfg_bom (id,tenant_id,bom_code,name,item_id,revision,description,status,created_by) "
                    "VALUES (:id,:t,:bc,:n,:iid,:rev,:desc,'draft',:cb)"),
               {"id": bid, "t": t, "bc": body.bom_code, "n": body.name, "iid": body.item_id,
                "rev": body.revision, "desc": body.description, "cb": user["id"]})
    for i, ln in enumerate(body.lines):
        lid = uid()
        db.execute(text("INSERT INTO dbp_mfg_bom_lines (id,tenant_id,bom_id,item_id,qty,unit,scrap_pct,cost_estimate,sort_order,notes) "
                        "VALUES (:id,:t,:bid,:iid,:qty,:u,:sc,:ce,:so,:n)"),
                   {"id": lid, "t": t, "bid": bid, "iid": ln.item_id, "qty": ln.qty,
                    "u": ln.unit, "sc": ln.scrap_pct, "ce": ln.cost_estimate,
                    "so": ln.sort_order or i, "n": ln.notes})
    audit_log(db, t, user["id"], "create", "mfg_bom", bid, new_values={"bom_code": body.bom_code})
    db.commit()
    return success_response("BOM created", {"id": bid, "bom_code": body.bom_code})

@router.get("/bom")
def list_bom(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT b.id,b.bom_code,b.name,b.item_id,b.revision,b.status,b.is_active,b.version "
                           "FROM dbp_mfg_bom b WHERE b.tenant_id=:t ORDER BY b.bom_code"), {"t": t}).fetchall()
    data = [{"id": r[0], "bom_code": r[1], "name": r[2], "item_id": r[3],
             "revision": r[4], "status": r[5], "is_active": r[6], "version": r[7]} for r in rows]
    return list_response(data, len(data))

@router.get("/bom/{bom_id}")
def get_bom(bom_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    b = db.execute(text("SELECT id,bom_code,name,item_id,revision,description,status,is_active,version "
                        "FROM dbp_mfg_bom WHERE id=:id AND tenant_id=:t"), {"id": bom_id, "t": t}).fetchone()
    if not b:
        raise HTTPException(404, detail="BOM not found")
    lines = db.execute(text("SELECT id,item_id,qty,unit,scrap_pct,cost_estimate,sort_order,notes "
                            "FROM dbp_mfg_bom_lines WHERE bom_id=:bid ORDER BY sort_order"), {"bid": bom_id}).fetchall()
    return success_response("BOM found", {
        "id": b[0], "bom_code": b[1], "name": b[2], "item_id": b[3],
        "revision": b[4], "description": b[5], "status": b[6],
        "is_active": b[7], "version": b[8],
        "lines": [{"id": l[0], "item_id": l[1], "qty": float(l[2]), "unit": l[3],
                    "scrap_pct": float(l[4]), "cost_estimate": float(l[5]),
                    "sort_order": l[6], "notes": l[7]} for l in lines]
    })

@router.put("/bom/{bom_id}/activate")
def activate_bom(bom_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    db.execute(text("UPDATE dbp_mfg_bom SET status='active', is_active=TRUE, updated_at=NOW() "
                    "WHERE id=:id AND tenant_id=:t"), {"id": bom_id, "t": t})
    audit_log(db, t, user["id"], "activate", "mfg_bom", bom_id, new_values={"status": "active"})
    db.commit()
    return success_response("BOM activated", {"id": bom_id})


# ═══════════════════════════════════════════════════
# WORK CENTERS
# ═══════════════════════════════════════════════════

class WorkCenterCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    work_center_type: str = "machine"
    capacity_per_hour: float = Field(default=1, gt=0)
    cost_per_hour: float = Field(default=0, ge=0)
    efficiency_pct: float = Field(default=100, ge=0, le=200)
    warehouse_id: Optional[str] = None

@router.post("/work-centers")
def create_work_center(body: WorkCenterCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_mfg_work_centers WHERE tenant_id=:t AND code=:c"),
                          {"t": t, "c": body.code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Work center code already exists")
    wid = uid()
    db.execute(text("INSERT INTO dbp_mfg_work_centers "
                    "(id,tenant_id,code,name,name_ar,work_center_type,capacity_per_hour,cost_per_hour,efficiency_pct,warehouse_id) "
                    "VALUES (:id,:t,:c,:n,:na,:wt,:cap,:ce,:eff,:wh)"),
               {"id": wid, "t": t, "c": body.code, "n": body.name, "na": body.name_ar,
                "wt": body.work_center_type, "cap": body.capacity_per_hour,
                "ce": body.cost_per_hour, "eff": body.efficiency_pct, "wh": body.warehouse_id})
    audit_log(db, t, user["id"], "create", "mfg_work_center", wid, new_values={"code": body.code})
    db.commit()
    return success_response("Work center created", {"id": wid, "code": body.code})

@router.get("/work-centers")
def list_work_centers(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,code,name,work_center_type,capacity_per_hour,cost_per_hour,efficiency_pct,status "
                           "FROM dbp_mfg_work_centers WHERE tenant_id=:t ORDER BY code"), {"t": t}).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "work_center_type": r[3],
             "capacity_per_hour": float(r[4]), "cost_per_hour": float(r[5]),
             "efficiency_pct": float(r[6]), "status": r[7]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# ROUTINGS
# ═══════════════════════════════════════════════════

class RoutingStepCreate(BaseModel):
    step_number: int = Field(ge=1)
    work_center_id: str
    setup_time_hrs: float = Field(default=0, ge=0)
    run_time_hrs: float = Field(default=0, ge=0)
    wait_time_hrs: float = Field(default=0, ge=0)
    transfer_time_hrs: float = Field(default=0, ge=0)
    description: Optional[str] = None

class RoutingCreate(BaseModel):
    routing_code: str
    name: str
    item_id: str
    bom_id: Optional[str] = None
    revision: str = "A"
    description: Optional[str] = None
    steps: List[RoutingStepCreate] = []

@router.post("/routings")
def create_routing(body: RoutingCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_mfg_routings WHERE tenant_id=:t AND routing_code=:c"),
                          {"t": t, "c": body.routing_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Routing code already exists")
    rid = uid()
    db.execute(text("INSERT INTO dbp_mfg_routings (id,tenant_id,routing_code,name,item_id,bom_id,revision,description,status) "
                    "VALUES (:id,:t,:rc,:n,:iid,:bid,:rev,:desc,'draft')"),
               {"id": rid, "t": t, "rc": body.routing_code, "n": body.name,
                "iid": body.item_id, "bid": body.bom_id, "rev": body.revision, "desc": body.description})
    for s in body.steps:
        sid = uid()
        db.execute(text("INSERT INTO dbp_mfg_routing_steps (id,tenant_id,routing_id,step_number,work_center_id,"
                        "setup_time_hrs,run_time_hrs,wait_time_hrs,transfer_time_hrs,description) "
                        "VALUES (:id,:t,:rid,:sn,:wcid,:st,:rt,:wt,:tt,:desc)"),
                   {"id": sid, "t": t, "rid": rid, "sn": s.step_number, "wcid": s.work_center_id,
                    "st": s.setup_time_hrs, "rt": s.run_time_hrs, "wt": s.wait_time_hrs,
                    "tt": s.transfer_time_hrs, "desc": s.description})
    audit_log(db, t, user["id"], "create", "mfg_routing", rid, new_values={"routing_code": body.routing_code})
    db.commit()
    return success_response("Routing created", {"id": rid, "routing_code": body.routing_code})

@router.get("/routings")
def list_routings(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,routing_code,name,item_id,revision,status,is_active "
                           "FROM dbp_mfg_routings WHERE tenant_id=:t ORDER BY routing_code"), {"t": t}).fetchall()
    data = [{"id": r[0], "routing_code": r[1], "name": r[2], "item_id": r[3],
             "revision": r[4], "status": r[5], "is_active": r[6]} for r in rows]
    return list_response(data, len(data))

@router.get("/routings/{routing_id}")
def get_routing(routing_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text("SELECT id,routing_code,name,item_id,bom_id,revision,description,status,is_active "
                        "FROM dbp_mfg_routings WHERE id=:id AND tenant_id=:t"), {"id": routing_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Routing not found")
    steps = db.execute(text("SELECT id,step_number,work_center_id,setup_time_hrs,run_time_hrs,wait_time_hrs,"
                            "transfer_time_hrs,description FROM dbp_mfg_routing_steps WHERE routing_id=:rid ORDER BY step_number"),
                       {"rid": routing_id}).fetchall()
    return success_response("Routing found", {
        "id": r[0], "routing_code": r[1], "name": r[2], "item_id": r[3],
        "bom_id": r[4], "revision": r[5], "description": r[6], "status": r[7], "is_active": r[8],
        "steps": [{"id": s[0], "step_number": s[1], "work_center_id": s[2],
                    "setup_time_hrs": float(s[3]), "run_time_hrs": float(s[4]),
                    "wait_time_hrs": float(s[5]), "transfer_time_hrs": float(s[6]),
                    "description": s[7]} for s in steps]
    })


# ═══════════════════════════════════════════════════
# PRODUCTION ORDERS
# ═══════════════════════════════════════════════════

class ProductionOrderCreate(BaseModel):
    item_id: str
    bom_id: Optional[str] = None
    routing_id: Optional[str] = None
    warehouse_id: str
    qty_planned: float = Field(gt=0)
    priority: int = Field(default=5, ge=1, le=10)
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    notes: Optional[str] = None

@router.post("/orders")
def create_production_order(body: ProductionOrderCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    order_num = _next_order_number(db, t)
    oid = uid()
    db.execute(text("INSERT INTO dbp_mfg_orders "
                    "(id,tenant_id,order_number,item_id,bom_id,routing_id,warehouse_id,qty_planned,status,priority,"
                    "planned_start,planned_end,notes,created_by) "
                    "VALUES (:id,:t,:on,:iid,:bid,:rid,:wid,:qp,'planned',:p,:ps,:pe,:n,:cb)"),
               {"id": oid, "t": t, "on": order_num, "iid": body.item_id,
                "bid": body.bom_id, "rid": body.routing_id, "wid": body.warehouse_id,
                "qp": body.qty_planned, "p": body.priority,
                "ps": body.planned_start, "pe": body.planned_end,
                "n": body.notes, "cb": user["id"]})
    audit_log(db, t, user["id"], "create", "mfg_order", oid,
              new_values={"order_number": order_num, "qty_planned": body.qty_planned})
    db.commit()
    return success_response("Production order created", {"id": oid, "order_number": order_num})

@router.get("/orders")
def list_orders(status: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE o.tenant_id=:t"
    params = {"t": t}
    if status:
        where += " AND o.status=:s"
        params["s"] = status
    rows = db.execute(text(f"SELECT o.id,o.order_number,o.item_id,o.qty_planned,o.qty_completed,o.qty_scrapped,"
                           f"o.status,o.priority,o.planned_start,o.planned_end,o.created_at "
                           f"FROM dbp_mfg_orders o {where} ORDER BY o.created_at DESC"), params).fetchall()
    data = [{"id": r[0], "order_number": r[1], "item_id": r[2],
             "qty_planned": float(r[3]), "qty_completed": float(r[4]), "qty_scrapped": float(r[5]),
             "status": r[6], "priority": r[7], "planned_start": str(r[8]) if r[8] else None,
             "planned_end": str(r[9]) if r[9] else None, "created_at": str(r[10]) if r[10] else None}
            for r in rows]
    return list_response(data, len(data))

@router.get("/orders/{order_id}")
def get_order(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    o = db.execute(text("SELECT id,order_number,item_id,bom_id,routing_id,warehouse_id,"
                        "qty_planned,qty_completed,qty_scrapped,status,priority,"
                        "planned_start,planned_end,actual_start,actual_end,notes,created_at "
                        "FROM dbp_mfg_orders WHERE id=:id AND tenant_id=:t"), {"id": order_id, "t": t}).fetchone()
    if not o:
        raise HTTPException(404, detail="Order not found")
    costs = db.execute(text("SELECT cost_type,SUM(amount) FROM dbp_mfg_costs WHERE order_id=:oid GROUP BY cost_type"),
                       {"oid": order_id}).fetchall()
    return success_response("Order found", {
        "id": o[0], "order_number": o[1], "item_id": o[2], "bom_id": o[3],
        "routing_id": o[4], "warehouse_id": o[5],
        "qty_planned": float(o[6]), "qty_completed": float(o[7]), "qty_scrapped": float(o[8]),
        "status": o[9], "priority": o[10],
        "planned_start": str(o[11]) if o[11] else None,
        "planned_end": str(o[12]) if o[12] else None,
        "actual_start": str(o[13]) if o[13] else None,
        "actual_end": str(o[14]) if o[14] else None,
        "notes": o[15], "created_at": str(o[16]) if o[16] else None,
        "costs": {r[0]: float(r[1]) for r in costs}
    })

@router.put("/orders/{order_id}/release")
def release_order(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    o = db.execute(text("SELECT status FROM dbp_mfg_orders WHERE id=:id AND tenant_id=:t"),
                   {"id": order_id, "t": t}).fetchone()
    if not o or o[0] != 'planned':
        raise HTTPException(400, detail="Only planned orders can be released")
    db.execute(text("UPDATE dbp_mfg_orders SET status='released', updated_at=NOW() WHERE id=:id"), {"id": order_id})
    audit_log(db, t, user["id"], "release", "mfg_order", order_id, old_values={"status": "planned"}, new_values={"status": "released"})
    db.commit()
    return success_response("Order released", {"id": order_id})

@router.put("/orders/{order_id}/start")
def start_order(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    o = db.execute(text("SELECT status FROM dbp_mfg_orders WHERE id=:id AND tenant_id=:t"),
                   {"id": order_id, "t": t}).fetchone()
    if not o or o[0] != 'released':
        raise HTTPException(400, detail="Only released orders can be started")
    db.execute(text("UPDATE dbp_mfg_orders SET status='in_progress', actual_start=NOW(), updated_at=NOW() WHERE id=:id"),
               {"id": order_id})
    audit_log(db, t, user["id"], "start", "mfg_order", order_id, old_values={"status": "released"}, new_values={"status": "in_progress"})
    db.commit()
    return success_response("Order started", {"id": order_id})

@router.put("/orders/{order_id}/complete")
def complete_order(order_id: str, qty_completed: float = Query(gt=0), user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    o = db.execute(text("SELECT status,qty_planned,qty_completed,item_id,warehouse_id FROM dbp_mfg_orders "
                        "WHERE id=:id AND tenant_id=:t"), {"id": order_id, "t": t}).fetchone()
    if not o:
        raise HTTPException(404, detail="Order not found")
    if o[0] != 'in_progress':
        raise HTTPException(400, detail="Only in-progress orders can be completed")
    new_completed = float(o[2] or 0) + qty_completed
    db.execute(text("UPDATE dbp_mfg_orders SET qty_completed=:qc, status='completed', actual_end=NOW(), updated_at=NOW() WHERE id=:id"),
               {"qc": new_completed, "id": order_id})
    atomic_stock_receive(db, t, o[3], qty_completed, 0, o[4], stock_table="dbp_commerce_stock", item_column="item_id")
    audit_log(db, t, user["id"], "complete", "mfg_order", order_id,
              new_values={"qty_completed": qty_completed, "status": "completed"})
    db.commit()
    return success_response("Order completed", {"id": order_id, "qty_completed": qty_completed})


# ═══════════════════════════════════════════════════
# MATERIAL ISSUES
# ═══════════════════════════════════════════════════

class MaterialIssueLineCreate(BaseModel):
    item_id: str
    qty_required: float = Field(gt=0)
    qty_issued: float = Field(default=0, ge=0)
    unit_cost: float = Field(default=0, ge=0)
    bom_line_id: Optional[str] = None

class MaterialIssueCreate(BaseModel):
    order_id: str
    warehouse_id: Optional[str] = None
    lines: List[MaterialIssueLineCreate] = []
    notes: Optional[str] = None

@router.post("/material-issues")
def create_material_issue(body: MaterialIssueCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    order = db.execute(text("SELECT id,warehouse_id FROM dbp_mfg_orders WHERE id=:oid AND tenant_id=:t"),
                       {"oid": body.order_id, "t": t}).fetchone()
    if not order:
        raise HTTPException(404, detail="Production order not found")
    issue_num = _next_issue_number(db, t)
    iid = uid()
    wh = body.warehouse_id or order[1]
    db.execute(text("INSERT INTO dbp_mfg_material_issues (id,tenant_id,order_id,issue_number,status,warehouse_id,notes) "
                    "VALUES (:id,:t,:oid,:in,'pending',:wh,:n)"),
               {"id": iid, "t": t, "oid": body.order_id, "in": issue_num, "wh": wh, "n": body.notes})
    for ln in body.lines:
        lid = uid()
        db.execute(text("INSERT INTO dbp_mfg_material_issue_lines "
                        "(id,tenant_id,issue_id,order_id,item_id,bom_line_id,qty_required,qty_issued,unit_cost,warehouse_id) "
                        "VALUES (:id,:t,:iid,:oid,:item,:bl,:qr,:qi,:uc,:wh)"),
                   {"id": lid, "t": t, "iid": iid, "oid": body.order_id, "item": ln.item_id,
                    "bl": ln.bom_line_id, "qr": ln.qty_required, "qi": ln.qty_issued,
                    "uc": ln.unit_cost, "wh": wh})
    audit_log(db, t, user["id"], "create", "mfg_material_issue", iid, new_values={"issue_number": issue_num})
    db.commit()
    return success_response("Material issue created", {"id": iid, "issue_number": issue_num})

@router.put("/material-issues/{issue_id}/issue")
def issue_materials(issue_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    mi = db.execute(text("SELECT status,order_id,warehouse_id FROM dbp_mfg_material_issues WHERE id=:id AND tenant_id=:t"),
                    {"id": issue_id, "t": t}).fetchone()
    if not mi or mi[0] != 'pending':
        raise HTTPException(400, detail="Only pending issues can be issued")
    lines = db.execute(text("SELECT id,item_id,qty_issued,unit_cost FROM dbp_mfg_material_issue_lines WHERE issue_id=:iid"),
                       {"iid": issue_id}).fetchall()
    if not lines:
        raise HTTPException(400, detail="No lines to issue")
    for ln in lines:
        if float(ln[2] or 0) <= 0:
            raise HTTPException(400, detail=f"Line {ln[0]} has zero qty_issued")
        atomic_stock_issue(db, t, ln[1], float(ln[2]), mi[2] or "default",
                           stock_table="dbp_commerce_stock", item_column="item_id")
    db.execute(text("UPDATE dbp_mfg_material_issues SET status='completed', issued_by=:ub, issued_at=NOW() WHERE id=:id"),
               {"ub": user["id"], "id": issue_id})
    total_cost = sum(float(ln[3] or 0) * float(ln[2] or 0) for ln in lines)
    company_id = get_company_id(db, t)
    post_journal(db, t, company_id, "mfg_material_issue", f"Material Issue {issue_id[:8]}",
                 [{"account_code": "5100", "description": "Material Cost", "debit": total_cost},
                  {"account_code": "1300", "description": "Inventory", "credit": total_cost}])
    audit_log(db, t, user["id"], "issue", "mfg_material_issue", issue_id, new_values={"status": "completed"})
    db.commit()
    return success_response("Materials issued", {"id": issue_id, "total_cost": total_cost})


# ═══════════════════════════════════════════════════
# PRODUCTION RECEIPTS
# ═══════════════════════════════════════════════════

class ReceiptCreate(BaseModel):
    order_id: str
    qty_received: float = Field(gt=0)
    qty_accepted: float = Field(gt=0)
    qty_rejected: float = Field(default=0, ge=0)
    warehouse_id: str
    unit_cost: float = Field(default=0, ge=0)
    notes: Optional[str] = None

@router.post("/receipts")
def create_receipt(body: ReceiptCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    order = db.execute(text("SELECT id,warehouse_id FROM dbp_mfg_orders WHERE id=:oid AND tenant_id=:t"),
                       {"oid": body.order_id, "t": t}).fetchone()
    if not order:
        raise HTTPException(404, detail="Production order not found")
    receipt_num = _next_receipt_number(db, t)
    rid = uid()
    db.execute(text("INSERT INTO dbp_mfg_receipts "
                    "(id,tenant_id,order_id,receipt_number,qty_received,qty_accepted,qty_rejected,warehouse_id,unit_cost,received_by) "
                    "VALUES (:id,:t,:oid,:rn,:qr,:qa,:qre,:wh,:uc,:rb)"),
               {"id": rid, "t": t, "oid": body.order_id, "rn": receipt_num,
                "qr": body.qty_received, "qa": body.qty_accepted, "qre": body.qty_rejected,
                "wh": body.warehouse_id, "uc": body.unit_cost, "rb": user["id"]})
    order_item = db.execute(text("SELECT item_id FROM dbp_mfg_orders WHERE id=:oid"), {"oid": body.order_id}).fetchone()
    if order_item and body.qty_accepted > 0:
        atomic_stock_receive(db, t, order_item[0], body.qty_accepted, body.unit_cost, body.warehouse_id,
                             stock_table="dbp_commerce_stock", item_column="item_id")
    company_id = get_company_id(db, t)
    total_cost = body.qty_accepted * body.unit_cost
    post_journal(db, t, company_id, "mfg_receipt", f"Production Receipt {receipt_num}",
                 [{"account_code": "1300", "description": "Finished Goods Inventory", "debit": total_cost},
                  {"account_code": "5000", "description": "WIP", "credit": total_cost}])
    audit_log(db, t, user["id"], "create", "mfg_receipt", rid,
              new_values={"receipt_number": receipt_num, "qty_accepted": body.qty_accepted})
    db.commit()
    return success_response("Receipt recorded", {"id": rid, "receipt_number": receipt_num})


# ═══════════════════════════════════════════════════
# QUALITY INSPECTIONS
# ═══════════════════════════════════════════════════

class InspectionCreate(BaseModel):
    order_id: Optional[str] = None
    receipt_id: Optional[str] = None
    item_id: str
    inspection_type: str = "incoming"
    qty_inspected: float = Field(default=0, ge=0)
    qty_passed: float = Field(default=0, ge=0)
    qty_failed: float = Field(default=0, ge=0)
    result: str = "pending"
    defect_notes: Optional[str] = None

@router.post("/quality-inspections")
def create_inspection(body: InspectionCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    insp_num = _next_inspection_number(db, t)
    iid = uid()
    db.execute(text("INSERT INTO dbp_mfg_quality_inspections "
                    "(id,tenant_id,inspection_number,order_id,receipt_id,item_id,inspection_type,"
                    "qty_inspected,qty_passed,qty_failed,result,inspector,defect_notes) "
                    "VALUES (:id,:t,:in,:oid,:rid,:iid,:it,:qi,:qp,:qf,:res,:insp,:dn)"),
               {"id": iid, "t": t, "in": insp_num, "oid": body.order_id, "rid": body.receipt_id,
                "iid": body.item_id, "it": body.inspection_type,
                "qi": body.qty_inspected, "qp": body.qty_passed, "qf": body.qty_failed,
                "res": body.result, "insp": user["id"], "dn": body.defect_notes})
    audit_log(db, t, user["id"], "create", "mfg_quality_inspection", iid,
              new_values={"inspection_number": insp_num, "result": body.result})
    db.commit()
    return success_response("Inspection recorded", {"id": iid, "inspection_number": insp_num})

@router.get("/quality-inspections")
def list_inspections(result: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params = {"t": t}
    if result:
        where += " AND result=:r"
        params["r"] = result
    rows = db.execute(text(f"SELECT id,inspection_number,order_id,receipt_id,item_id,inspection_type,"
                           f"qty_inspected,qty_passed,qty_failed,result,inspection_date "
                           f"FROM dbp_mfg_quality_inspections {where} ORDER BY created_at DESC"), params).fetchall()
    data = [{"id": r[0], "inspection_number": r[1], "order_id": r[2], "receipt_id": r[3],
             "item_id": r[4], "inspection_type": r[5],
             "qty_inspected": float(r[6]), "qty_passed": float(r[7]), "qty_failed": float(r[8]),
             "result": r[9], "inspection_date": str(r[10]) if r[10] else None} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# SCRAP
# ═══════════════════════════════════════════════════

class ScrapCreate(BaseModel):
    order_id: str
    item_id: str
    qty: float = Field(gt=0)
    reason: Optional[str] = None
    cost: float = Field(default=0, ge=0)

@router.post("/scrap")
def create_scrap(body: ScrapCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    sid = uid()
    db.execute(text("INSERT INTO dbp_mfg_scrap (id,tenant_id,order_id,item_id,qty,reason,cost,reported_by) "
                    "VALUES (:id,:t,:oid,:iid,:qty,:r,:c,:rb)"),
               {"id": sid, "t": t, "oid": body.order_id, "iid": body.item_id,
                "qty": body.qty, "r": body.reason, "c": body.cost, "rb": user["id"]})
    db.execute(text("UPDATE dbp_mfg_orders SET qty_scrapped=qty_scrapped+:q, updated_at=NOW() WHERE id=:oid"),
               {"q": body.qty, "oid": body.order_id})
    if body.cost > 0:
        company_id = get_company_id(db, t)
        post_journal(db, t, company_id, "mfg_scrap", f"Scrap {sid[:8]}",
                     [{"account_code": "5200", "description": "Scrap Loss", "debit": body.cost},
                      {"account_code": "1300", "description": "Inventory", "credit": body.cost}])
    audit_log(db, t, user["id"], "create", "mfg_scrap", sid,
              new_values={"qty": body.qty, "reason": body.reason})
    db.commit()
    return success_response("Scrap recorded", {"id": sid})


# ═══════════════════════════════════════════════════
# MANUFACTURING DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/dashboard")
def manufacturing_dashboard(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]

    planned = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='planned'"), {"t": t}).fetchone()[0] or 0
    released = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='released'"), {"t": t}).fetchone()[0] or 0
    in_progress = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='in_progress'"), {"t": t}).fetchone()[0] or 0
    completed = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='completed'"), {"t": t}).fetchone()[0] or 0
    total_orders = planned + released + in_progress + completed

    total_planned = db.execute(text("SELECT COALESCE(SUM(qty_planned),0) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    total_completed = db.execute(text("SELECT COALESCE(SUM(qty_completed),0) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    total_scrapped = db.execute(text("SELECT COALESCE(SUM(qty_scrapped),0) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0

    yield_rate = float(total_completed) / float(total_completed + total_scrapped) * 100 if (total_completed + total_scrapped) > 0 else 100

    pending_issues = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_material_issues WHERE tenant_id=:t AND status='pending'"), {"t": t}).fetchone()[0] or 0
    pending_qi = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_quality_inspections WHERE tenant_id=:t AND result='pending'"), {"t": t}).fetchone()[0] or 0

    boms = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_bom WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    work_centers = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_work_centers WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0
    routings = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_routings WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0

    return success_response("Manufacturing dashboard", {
        "orders": {"planned": planned, "released": released, "in_progress": in_progress, "completed": completed, "total": total_orders},
        "production": {"total_planned": float(total_planned), "total_completed": float(total_completed), "total_scrapped": float(total_scrapped), "yield_rate": round(yield_rate, 1)},
        "pending": {"material_issues": pending_issues, "quality_inspections": pending_qi},
        "master_data": {"boms": boms, "work_centers": work_centers, "routings": routings},
    })


# ═══════════════════════════════════════════════════
# COSTS
# ═══════════════════════════════════════════════════

class CostCreate(BaseModel):
    order_id: str
    cost_type: str
    amount: float = Field(ge=0)
    description: Optional[str] = None
    account_code: Optional[str] = None

@router.post("/costs")
def add_cost(body: CostCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    cid = uid()
    db.execute(text("INSERT INTO dbp_mfg_costs (id,tenant_id,order_id,cost_type,amount,description,account_code) "
                    "VALUES (:id,:t,:oid,:ct,:a,:d,:ac)"),
               {"id": cid, "t": t, "oid": body.order_id, "ct": body.cost_type,
                "a": body.amount, "d": body.description, "ac": body.account_code})
    audit_log(db, t, user["id"], "create", "mfg_cost", cid,
              new_values={"cost_type": body.cost_type, "amount": body.amount})
    db.commit()
    return success_response("Cost recorded", {"id": cid})

@router.get("/costs/{order_id}")
def list_costs(order_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text("SELECT id,cost_type,amount,description,account_code,created_at "
                           "FROM dbp_mfg_costs WHERE order_id=:oid AND tenant_id=:t ORDER BY created_at"),
                      {"oid": order_id, "t": t}).fetchall()
    data = [{"id": r[0], "cost_type": r[1], "amount": float(r[2]),
             "description": r[3], "account_code": r[4], "created_at": str(r[5]) if r[5] else None}
            for r in rows]
    total = sum(d["amount"] for d in data)
    return list_response({"items": data, "total_cost": total}, len(data))
