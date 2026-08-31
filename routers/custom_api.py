"""
P71.5 Dynamic Customization Layer — API
=========================================
Custom fields, modules, records, and workflows.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from database import get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, check_permission, audit_log,
    success_response, list_response,
)

router = APIRouter(prefix="/custom", tags=["Dynamic Customization"])


# ═══════════════════════════════════════════════════
# CUSTOM FIELDS
# ═══════════════════════════════════════════════════

class FieldCreate(BaseModel):
    entity_type: str
    field_code: str
    field_label: str
    field_type: str = "text"
    is_required: bool = False
    default_value: Optional[str] = None
    enum_values: Optional[str] = None
    sort_order: int = 0

@router.post("/fields")
def create_field(body: FieldCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_types = {"text", "number", "date", "boolean", "select", "multiselect", "email", "phone", "url", "currency", "textarea"}
    if body.field_type not in valid_types:
        raise HTTPException(400, detail=f"Invalid field_type. Must be one of: {valid_types}")
    existing = db.execute(text(
        "SELECT id FROM dbp_custom_fields WHERE tenant_id=:t AND entity_type=:et AND field_code=:fc"),
        {"t": t, "et": body.entity_type, "fc": body.field_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Field code already exists for this entity")
    fid = uid()
    db.execute(text("INSERT INTO dbp_custom_fields "
                    "(id,tenant_id,entity_type,field_code,field_label,field_type,is_required,default_value,enum_values,sort_order) "
                    "VALUES (:id,:t,:et,:fc,:fl,:ft,:ir,:dv,:eo,:so)"),
               {"id": fid, "t": t, "et": body.entity_type, "fc": body.field_code,
                "fl": body.field_label, "ft": body.field_type, "ir": body.is_required,
                "dv": body.default_value, "eo": body.enum_values, "so": body.sort_order})
    audit_log(db, t, user["id"], "create", "custom_field", fid, new_values={"entity_type": body.entity_type, "field_code": body.field_code})
    db.commit()
    return success_response("Field created", {"id": fid})

@router.get("/fields")
def list_fields(entity_type: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t AND is_active=TRUE"
    params: Dict[str, Any] = {"t": t}
    if entity_type:
        where += " AND entity_type=:et"
        params["et"] = entity_type
    rows = db.execute(text(
        f"SELECT id,entity_type,field_code,field_label,field_type,is_required,default_value,enum_values,sort_order "
        f"FROM dbp_custom_fields {where} ORDER BY entity_type, sort_order"), params).fetchall()
    data = [{"id": r[0], "entity_type": r[1], "field_code": r[2], "field_label": r[3],
             "field_type": r[4], "is_required": r[5], "default_value": r[6],
             "enum_values": r[7], "sort_order": r[8]} for r in rows]
    return list_response(data, len(data))

@router.delete("/fields/{field_id}")
def delete_field(field_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    f = db.execute(text("SELECT id FROM dbp_custom_fields WHERE id=:id AND tenant_id=:t"),
                   {"id": field_id, "t": t}).fetchone()
    if not f:
        raise HTTPException(404, detail="Field not found")
    db.execute(text("DELETE FROM dbp_custom_field_values WHERE field_id=:fid"), {"fid": field_id})
    db.execute(text("DELETE FROM dbp_custom_fields WHERE id=:id"), {"id": field_id})
    audit_log(db, t, user["id"], "delete", "custom_field", field_id)
    db.commit()
    return success_response("Field deleted", {"id": field_id})


# ═══════════════════════════════════════════════════
# FIELD VALUES
# ═══════════════════════════════════════════════════

class FieldValueSet(BaseModel):
    entity_type: str
    entity_id: str
    field_id: str
    field_value: str

@router.post("/fields/values")
def set_field_value(body: FieldValueSet, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    field = db.execute(text("SELECT id FROM dbp_custom_fields WHERE id=:fid AND tenant_id=:t AND is_active=TRUE"),
                       {"fid": body.field_id, "t": t}).fetchone()
    if not field:
        raise HTTPException(400, detail="Field not found")
    existing = db.execute(text(
        "SELECT id FROM dbp_custom_field_values WHERE tenant_id=:t AND entity_type=:et AND entity_id=:ei AND field_id=:fid"),
        {"t": t, "et": body.entity_type, "ei": body.entity_id, "fid": body.field_id}).fetchone()
    if existing:
        db.execute(text("UPDATE dbp_custom_field_values SET field_value=:fv, updated_at=NOW() WHERE id=:id"),
                   {"fv": body.field_value, "id": existing[0]})
    else:
        vid = uid()
        db.execute(text("INSERT INTO dbp_custom_field_values "
                        "(id,tenant_id,entity_type,entity_id,field_id,field_value) "
                        "VALUES (:id,:t,:et,:ei,:fid,:fv)"),
                   {"id": vid, "t": t, "et": body.entity_type, "ei": body.entity_id,
                    "fid": body.field_id, "fv": body.field_value})
    db.commit()
    return success_response("Field value set", {"entity_type": body.entity_type, "entity_id": body.entity_id})

@router.get("/fields/values")
def get_field_values(entity_type: str, entity_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT f.field_code, f.field_label, f.field_type, v.field_value "
        "FROM dbp_custom_field_values v JOIN dbp_custom_fields f ON v.field_id = f.id "
        "WHERE v.tenant_id=:t AND v.entity_type=:et AND v.entity_id=:ei"),
        {"t": t, "et": entity_type, "ei": entity_id}).fetchall()
    data = [{"field_code": r[0], "field_label": r[1], "field_type": r[2], "field_value": r[3]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# CUSTOM MODULES
# ═══════════════════════════════════════════════════

class ModuleCreate(BaseModel):
    module_code: str
    module_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    fields: Optional[List[Dict[str, Any]]] = None

@router.post("/modules")
def create_module(body: ModuleCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_custom_modules WHERE tenant_id=:t AND module_code=:mc"),
                          {"t": t, "mc": body.module_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Module code already exists")
    mid = uid()
    config_json = json.dumps({"icon": body.icon, "color": body.color}) if body.icon or body.color else None
    db.execute(text("INSERT INTO dbp_custom_modules (id,tenant_id,module_code,module_name,description,icon,color,config) "
                    "VALUES (:id,:t,:mc,:mn,:d,:i,:c,:cfg)"),
               {"id": mid, "t": t, "mc": body.module_code, "mn": body.module_name,
                "d": body.description, "i": body.icon, "c": body.color, "cfg": config_json})
    if body.fields:
        for i, f in enumerate(body.fields):
            fid = uid()
            db.execute(text("INSERT INTO dbp_custom_module_fields "
                            "(id,tenant_id,module_id,field_code,field_label,field_type,is_required,is_primary,sort_order) "
                            "VALUES (:id,:t,:mid,:fc,:fl,:ft,:ir,:ip,:so)"),
                       {"id": fid, "t": t, "mid": mid, "fc": f.get("field_code", f"field_{i}"),
                        "fl": f.get("field_label", f"Field {i}"), "ft": f.get("field_type", "text"),
                        "ir": f.get("is_required", False), "ip": f.get("is_primary", False), "so": i})
    audit_log(db, t, user["id"], "create", "custom_module", mid, new_values={"module_code": body.module_code})
    db.commit()
    return success_response("Module created", {"id": mid})

@router.get("/modules")
def list_modules(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,module_code,module_name,description,icon,color,is_active "
        "FROM dbp_custom_modules WHERE tenant_id=:t AND is_active=TRUE ORDER BY module_name"), {"t": t}).fetchall()
    data = []
    for r in rows:
        fields = db.execute(text(
            "SELECT id,field_code,field_label,field_type,is_required,is_primary,sort_order "
            "FROM dbp_custom_module_fields WHERE module_id=:mid ORDER BY sort_order"), {"mid": r[0]}).fetchall()
        record_count = db.execute(text(
            "SELECT COUNT(*) FROM dbp_custom_module_records WHERE module_id=:mid AND status='active'"), {"mid": r[0]}).fetchone()[0] or 0
        data.append({
            "id": r[0], "module_code": r[1], "module_name": r[2], "description": r[3],
            "icon": r[4], "color": r[5], "is_active": r[6], "record_count": record_count,
            "fields": [{"id": f[0], "field_code": f[1], "field_label": f[2], "field_type": f[3],
                        "is_required": f[4], "is_primary": f[5], "sort_order": f[6]} for f in fields]
        })
    return list_response(data, len(data))

@router.get("/modules/{module_id}")
def get_module(module_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,module_code,module_name,description,icon,color,is_active "
        "FROM dbp_custom_modules WHERE id=:id AND tenant_id=:t"), {"id": module_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Module not found")
    fields = db.execute(text(
        "SELECT id,field_code,field_label,field_type,is_required,is_primary,sort_order "
        "FROM dbp_custom_module_fields WHERE module_id=:mid ORDER BY sort_order"), {"mid": module_id}).fetchall()
    return success_response("Module details", {
        "id": r[0], "module_code": r[1], "module_name": r[2], "description": r[3],
        "icon": r[4], "color": r[5], "is_active": r[6],
        "fields": [{"id": f[0], "field_code": f[1], "field_label": f[2], "field_type": f[3],
                    "is_required": f[4], "is_primary": f[5], "sort_order": f[6]} for f in fields]
    })

@router.delete("/modules/{module_id}")
def delete_module(module_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    m = db.execute(text("SELECT id FROM dbp_custom_modules WHERE id=:id AND tenant_id=:t"),
                   {"id": module_id, "t": t}).fetchone()
    if not m:
        raise HTTPException(404, detail="Module not found")
    db.execute(text("DELETE FROM dbp_custom_module_records WHERE module_id=:mid"), {"mid": module_id})
    db.execute(text("DELETE FROM dbp_custom_module_fields WHERE module_id=:mid"), {"mid": module_id})
    db.execute(text("DELETE FROM dbp_custom_modules WHERE id=:id"), {"id": module_id})
    audit_log(db, t, user["id"], "delete", "custom_module", module_id)
    db.commit()
    return success_response("Module deleted", {"id": module_id})


# ═══════════════════════════════════════════════════
# MODULE RECORDS
# ═══════════════════════════════════════════════════

class RecordCreate(BaseModel):
    record_code: Optional[str] = None
    data: Dict[str, Any]

@router.post("/modules/{module_id}/records")
def create_record(module_id: str, body: RecordCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    m = db.execute(text("SELECT id FROM dbp_custom_modules WHERE id=:id AND tenant_id=:t AND is_active=TRUE"),
                   {"id": module_id, "t": t}).fetchone()
    if not m:
        raise HTTPException(404, detail="Module not found")
    rid = uid()
    data_json = json.dumps(body.data)
    db.execute(text("INSERT INTO dbp_custom_module_records "
                    "(id,tenant_id,module_id,record_code,data,created_by) "
                    "VALUES (:id,:t,:mid,:rc,:d,:cb)"),
               {"id": rid, "t": t, "mid": module_id, "rc": body.record_code, "d": data_json, "cb": user["id"]})
    audit_log(db, t, user["id"], "create", "custom_record", rid, new_values={"module_id": module_id})
    db.commit()
    return success_response("Record created", {"id": rid})

@router.get("/modules/{module_id}/records")
def list_records(module_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,record_code,data,status,created_by,created_at "
        "FROM dbp_custom_module_records WHERE module_id=:mid AND tenant_id=:t AND status != 'deleted' "
        "ORDER BY created_at DESC LIMIT 100"),
        {"mid": module_id, "t": t}).fetchall()
    data = [{"id": r[0], "record_code": r[1], "data": r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] and isinstance(r[2], str) else {}),
             "status": r[3], "created_by": r[4],
             "created_at": str(r[5]) if r[5] else None} for r in rows]
    return list_response(data, len(data))

@router.put("/modules/{module_id}/records/{record_id}")
def update_record(module_id: str, record_id: str, body: RecordCreate,
                  user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    r = db.execute(text("SELECT id FROM dbp_custom_module_records WHERE id=:rid AND module_id=:mid AND tenant_id=:t"),
                   {"rid": record_id, "mid": module_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Record not found")
    data_json = json.dumps(body.data)
    db.execute(text("UPDATE dbp_custom_module_records SET data=:d, record_code=:rc, updated_at=NOW() WHERE id=:id"),
               {"d": data_json, "rc": body.record_code, "id": record_id})
    db.commit()
    return success_response("Record updated", {"id": record_id})

@router.delete("/modules/{module_id}/records/{record_id}")
def delete_record(module_id: str, record_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    db.execute(text("UPDATE dbp_custom_module_records SET status='deleted', updated_at=NOW() "
                    "WHERE id=:rid AND module_id=:mid AND tenant_id=:t"),
               {"rid": record_id, "mid": module_id, "t": t})
    db.commit()
    return success_response("Record deleted", {"id": record_id})


# ═══════════════════════════════════════════════════
# WORKFLOWS
# ═══════════════════════════════════════════════════

class WorkflowCreate(BaseModel):
    workflow_name: str
    entity_type: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]

@router.post("/workflows")
def create_workflow(body: WorkflowCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    wid = uid()
    db.execute(text("INSERT INTO dbp_custom_workflows (id,tenant_id,workflow_name,entity_type,description) "
                    "VALUES (:id,:t,:wn,:et,:d)"),
               {"id": wid, "t": t, "wn": body.workflow_name, "et": body.entity_type, "d": body.description})
    for i, step in enumerate(body.steps):
        sid = uid()
        action_config = json.dumps(step.get("action_config")) if step.get("action_config") else None
        db.execute(text("INSERT INTO dbp_workflow_steps "
                        "(id,tenant_id,workflow_id,step_order,step_name,action_type,action_config,"
                        "next_step_on_success,next_step_on_failure) "
                        "VALUES (:id,:t,:wid,:so,:sn,:at,:ac,:nss,:nsf)"),
                   {"id": sid, "t": t, "wid": wid, "so": step.get("step_order", i + 1),
                    "sn": step.get("step_name", f"Step {i+1}"),
                    "at": step.get("action_type", "approve"),
                    "ac": action_config,
                    "nss": step.get("next_step_on_success"),
                    "nsf": step.get("next_step_on_failure")})
    audit_log(db, t, user["id"], "create", "custom_workflow", wid, new_values={"workflow_name": body.workflow_name})
    db.commit()
    return success_response("Workflow created", {"id": wid})

@router.get("/workflows")
def list_workflows(entity_type: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t AND is_active=TRUE"
    params: Dict[str, Any] = {"t": t}
    if entity_type:
        where += " AND entity_type=:et"
        params["et"] = entity_type
    rows = db.execute(text(
        f"SELECT id,workflow_name,entity_type,description FROM dbp_custom_workflows {where} ORDER BY workflow_name"),
        params).fetchall()
    data = [{"id": r[0], "workflow_name": r[1], "entity_type": r[2], "description": r[3]} for r in rows]
    return list_response(data, len(data))

@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,workflow_name,entity_type,description,is_active "
        "FROM dbp_custom_workflows WHERE id=:id AND tenant_id=:t"),
        {"id": workflow_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Workflow not found")
    steps = db.execute(text(
        "SELECT step_order,step_name,action_type,action_config,next_step_on_success,next_step_on_failure "
        "FROM dbp_workflow_steps WHERE workflow_id=:wid ORDER BY step_order"),
        {"wid": workflow_id}).fetchall()
    instances = db.execute(text(
        "SELECT COUNT(*) FROM dbp_workflow_instances_v2 WHERE workflow_id=:wid AND status='running'"),
        {"wid": workflow_id}).fetchone()[0] or 0
    return success_response("Workflow details", {
        "id": r[0], "workflow_name": r[1], "entity_type": r[2], "description": r[3], "is_active": r[4],
        "steps": [{"step_order": s[0], "step_name": s[1], "action_type": s[2],
                   "action_config": json.loads(s[3]) if s[3] else None,
                   "next_step_on_success": s[4], "next_step_on_failure": s[5]} for s in steps],
        "running_instances": instances
    })

@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "delete")
    t = user["tenant_id"]
    w = db.execute(text("SELECT id FROM dbp_custom_workflows WHERE id=:id AND tenant_id=:t"),
                   {"id": workflow_id, "t": t}).fetchone()
    if not w:
        raise HTTPException(404, detail="Workflow not found")
    running = db.execute(text("SELECT COUNT(*) FROM dbp_workflow_instances_v2 WHERE workflow_id=:wid AND status='running'"),
                         {"wid": workflow_id}).fetchone()[0] or 0
    if running > 0:
        raise HTTPException(400, detail="Cannot delete workflow with running instances")
    db.execute(text("DELETE FROM dbp_workflow_log WHERE instance_id IN (SELECT id FROM dbp_workflow_instances_v2 WHERE workflow_id=:wid)"),
               {"wid": workflow_id})
    db.execute(text("DELETE FROM dbp_workflow_instances_v2 WHERE workflow_id=:wid"), {"wid": workflow_id})
    db.execute(text("DELETE FROM dbp_workflow_steps WHERE workflow_id=:wid"), {"wid": workflow_id})
    db.execute(text("DELETE FROM dbp_custom_workflows WHERE id=:id"), {"id": workflow_id})
    audit_log(db, t, user["id"], "delete", "custom_workflow", workflow_id)
    db.commit()
    return success_response("Workflow deleted", {"id": workflow_id})


# ═══════════════════════════════════════════════════
# WORKFLOW EXECUTION
# ═══════════════════════════════════════════════════

class WorkflowStart(BaseModel):
    workflow_id: str
    entity_type: str
    entity_id: str

@router.post("/workflows/start")
def start_workflow(body: WorkflowStart, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    w = db.execute(text("SELECT id FROM dbp_custom_workflows WHERE id=:wid AND tenant_id=:t AND is_active=TRUE"),
                   {"wid": body.workflow_id, "t": t}).fetchone()
    if not w:
        raise HTTPException(404, detail="Workflow not found")
    iid = uid()
    db.execute(text("INSERT INTO dbp_workflow_instances_v2 "
                    "(id,tenant_id,workflow_id,entity_type,entity_id,current_step,status) "
                    "VALUES (:id,:t,:wid,:et,:ei,1,'running')"),
               {"id": iid, "t": t, "wid": body.workflow_id, "et": body.entity_type, "ei": body.entity_id})
    _log_workflow(db, t, iid, 1, "started", "running", user["id"], "Workflow started")
    db.commit()
    return success_response("Workflow started", {"instance_id": iid})

class WorkflowStepAction(BaseModel):
    action: str  # "approve" or "reject"
    comment: Optional[str] = None

@router.post("/workflows/instances/{instance_id}/step")
def execute_step(instance_id: str, body: WorkflowStepAction,
                 user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    inst = db.execute(text(
        "SELECT id,workflow_id,current_step,status FROM dbp_workflow_instances_v2 WHERE id=:id AND tenant_id=:t"),
        {"id": instance_id, "t": t}).fetchone()
    if not inst:
        raise HTTPException(404, detail="Instance not found")
    if inst[3] != "running":
        raise HTTPException(400, detail=f"Workflow is {inst[3]}")
    current_step = inst[2]
    step = db.execute(text(
        "SELECT id,action_type,next_step_on_success,next_step_on_failure "
        "FROM dbp_workflow_steps WHERE workflow_id=:wid AND step_order=:so"),
        {"wid": inst[1], "so": current_step}).fetchone()
    if not step:
        db.execute(text("UPDATE dbp_workflow_instances_v2 SET status='completed', completed_at=NOW() WHERE id=:id"),
                   {"id": instance_id})
        _log_workflow(db, t, instance_id, current_step, "completed", "completed", user["id"], "All steps done")
        db.commit()
        return success_response("Workflow completed", {"instance_id": instance_id})
    if body.action == "approve":
        next_step = step[2]
        result = "approved"
    elif body.action == "reject":
        next_step = step[3]
        result = "rejected"
    else:
        raise HTTPException(400, detail="Action must be 'approve' or 'reject'")
    _log_workflow(db, t, instance_id, current_step, body.action, result, user["id"], body.comment)
    if next_step is None or (body.action == "reject" and next_step is None):
        db.execute(text("UPDATE dbp_workflow_instances_v2 SET status='completed', completed_at=NOW() WHERE id=:id"),
                   {"id": instance_id})
        _log_workflow(db, t, instance_id, current_step, "completed", "completed", user["id"], "Workflow completed")
    else:
        db.execute(text("UPDATE dbp_workflow_instances_v2 SET current_step=:ns WHERE id=:id"),
                   {"ns": next_step, "id": instance_id})
    db.commit()
    return success_response("Step executed", {"action": body.action, "next_step": next_step})

@router.get("/workflows/instances/{instance_id}")
def get_instance(instance_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,workflow_id,entity_type,entity_id,current_step,status,started_at,completed_at "
        "FROM dbp_workflow_instances_v2 WHERE id=:id AND tenant_id=:t"),
        {"id": instance_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Instance not found")
    log = db.execute(text(
        "SELECT step_order,action,result,actor_id,details,created_at "
        "FROM dbp_workflow_log WHERE instance_id=:iid ORDER BY created_at"),
        {"iid": instance_id}).fetchall()
    return success_response("Instance details", {
        "id": r[0], "workflow_id": r[1], "entity_type": r[2], "entity_id": r[3],
        "current_step": r[4], "status": r[5],
        "started_at": str(r[6]) if r[6] else None,
        "completed_at": str(r[7]) if r[7] else None,
        "log": [{"step_order": l[0], "action": l[1], "result": l[2], "actor_id": l[3],
                 "details": l[4], "created_at": str(l[5]) if l[5] else None} for l in log]
    })


# ═══════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════

@router.get("/stats")
def customization_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    fields = db.execute(text("SELECT COUNT(*) FROM dbp_custom_fields WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    modules = db.execute(text("SELECT COUNT(*) FROM dbp_custom_modules WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    records = db.execute(text("SELECT COUNT(*) FROM dbp_custom_module_records WHERE tenant_id=:t AND status='active'"), {"t": t}).fetchone()[0] or 0
    workflows = db.execute(text("SELECT COUNT(*) FROM dbp_custom_workflows WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    running = db.execute(text("SELECT COUNT(*) FROM dbp_workflow_instances_v2 WHERE tenant_id=:t AND status='running'"), {"t": t}).fetchone()[0] or 0
    return success_response("Customization stats", {
        "custom_fields": fields, "custom_modules": modules, "module_records": records,
        "workflows": workflows, "running_workflows": running
    })


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _log_workflow(db, tenant_id, instance_id, step_order, action, result, actor_id, details):
    lid = uid()
    db.execute(text("INSERT INTO dbp_workflow_log "
                    "(id,tenant_id,instance_id,step_order,action,result,actor_id,details) "
                    "VALUES (:id,:t,:ii,:so,:a,:r,:ai,:d)"),
               {"id": lid, "t": tenant_id, "ii": instance_id, "so": step_order,
                "a": action, "r": result, "ai": actor_id, "d": details})
