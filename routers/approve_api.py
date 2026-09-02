"""
P71.2 Universal Approval Engine — API
=======================================
Configurable multi-step approval chains for any module.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from core.industry_security import (
    audit_log,
    check_permission,
    list_response,
    success_response,
    uid,
)
from database import get_db

router = APIRouter(prefix="/approvals", tags=["Approval Engine"])


# ═══════════════════════════════════════════════════
# CHAINS
# ═══════════════════════════════════════════════════

class StepDef(BaseModel):
    step_order: int
    step_name: str
    approver_type: str = "user"
    approver_value: str | None = None
    min_approvals: int = 1
    is_optional: bool = False

class ChainCreate(BaseModel):
    chain_name: str
    source_module: str
    description: str | None = None
    steps: list[StepDef]

@router.post("/chains")
def create_chain(body: ChainCreate, user: dict | None=None, db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_approve_chains WHERE tenant_id=:t AND chain_name=:cn"),
                          {"t": t, "cn": body.chain_name}).fetchone()
    if existing:
        raise HTTPException(400, detail="Chain name already exists")
    cid = uid()
    db.execute(text("INSERT INTO dbp_approve_chains (id,tenant_id,chain_name,source_module,description) "
                    "VALUES (:id,:t,:cn,:sm,:d)"),
               {"id": cid, "t": t, "cn": body.chain_name, "sm": body.source_module, "d": body.description})
    for step in body.steps:
        if step.approver_type not in ("user", "role", "manager", "self_manager", "any_role"):
            raise HTTPException(400, detail=f"Invalid approver_type: {step.approver_type}")
        sid = uid()
        db.execute(text("INSERT INTO dbp_approve_steps "
                        "(id,tenant_id,chain_id,step_order,step_name,approver_type,approver_value,min_approvals,is_optional) "
                        "VALUES (:id,:t,:cid,:so,:sn,:at,:av,:mo,:io)"),
                   {"id": sid, "t": t, "cid": cid, "so": step.step_order, "sn": step.step_name,
                    "at": step.approver_type, "av": step.approver_value,
                    "mo": step.min_approvals, "io": step.is_optional})
    audit_log(db, t, user["id"], "create", "approve_chain", cid, new_values={"chain_name": body.chain_name})
    db.commit()
    return success_response("Chain created", {"id": cid, "steps": len(body.steps)})

@router.get("/chains")
def list_chains(source_module: str | None = None, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params: dict[str, Any] = {"t": t}
    if source_module:
        where += " AND source_module=:sm"
        params["sm"] = source_module
    rows = db.execute(text(
        f"SELECT id,chain_name,source_module,description,is_active FROM dbp_approve_chains {where} ORDER BY chain_name"), params).fetchall()
    data = [{"id": r[0], "chain_name": r[1], "source_module": r[2], "description": r[3], "is_active": r[4]} for r in rows]
    return list_response(data, len(data))

@router.get("/chains/{chain_id}/steps")
def get_chain_steps(chain_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,step_order,step_name,approver_type,approver_value,min_approvals,is_optional "
        "FROM dbp_approve_steps WHERE chain_id=:cid AND tenant_id=:t ORDER BY step_order"),
        {"cid": chain_id, "t": t}).fetchall()
    data = [{"id": r[0], "step_order": r[1], "step_name": r[2], "approver_type": r[3],
             "approver_value": r[4], "min_approvals": r[5], "is_optional": r[6]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# REQUESTS
# ═══════════════════════════════════════════════════

class RequestCreate(BaseModel):
    chain_id: str | None = None
    source_module: str
    source_id: str
    title: str
    description: str | None = None

@router.post("/requests")
def create_request(body: RequestCreate, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rid = uid()
    db.execute(text("INSERT INTO dbp_approve_requests "
                    "(id,tenant_id,chain_id,source_module,source_id,title,description,requested_by) "
                    "VALUES (:id,:t,:cid,:sm,:si,:ti,:d,:rb)"),
               {"id": rid, "t": t, "cid": body.chain_id, "sm": body.source_module,
                "si": body.source_id, "ti": body.title, "d": body.description, "rb": user["id"]})
    _log_action(db, t, rid, "created", user["id"], f"Request created: {body.title}")
    audit_log(db, t, user["id"], "create", "approve_request", rid, new_values={"title": body.title})
    db.commit()
    return success_response("Approval request created", {"id": rid})

@router.get("/requests")
def list_requests(status: str | None = None, source_module: str | None = None,
                  user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    where = "WHERE tenant_id=:t"
    params: dict[str, Any] = {"t": t}
    if status:
        where += " AND status=:s"
        params["s"] = status
    if source_module:
        where += " AND source_module=:sm"
        params["sm"] = source_module
    rows = db.execute(text(
        f"SELECT id,source_module,source_id,title,requested_by,current_step,status,created_at "
        f"FROM dbp_approve_requests {where} ORDER BY created_at DESC LIMIT 100"), params).fetchall()
    data = [{"id": r[0], "source_module": r[1], "source_id": r[2], "title": r[3],
             "requested_by": r[4], "current_step": r[5], "status": r[6],
             "created_at": str(r[7]) if r[7] else None} for r in rows]
    return list_response(data, len(data))

@router.get("/requests/{request_id}")
def get_request(request_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    r = db.execute(text(
        "SELECT id,chain_id,source_module,source_id,title,description,requested_by,"
        "current_step,status,created_at,updated_at,completed_at "
        "FROM dbp_approve_requests WHERE id=:id AND tenant_id=:t"), {"id": request_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Request not found")
    actions = db.execute(text(
        "SELECT step_order,approver_id,decision,comment,decided_at "
        "FROM dbp_approve_actions WHERE request_id=:rid ORDER BY decided_at"),
        {"rid": request_id}).fetchall()
    steps = db.execute(text(
        "SELECT step_order,step_name,approver_type,approver_value,min_approvals,is_optional "
        "FROM dbp_approve_steps WHERE chain_id=:cid AND tenant_id=:t ORDER BY step_order"),
        {"cid": r[0], "t": t}).fetchall()
    return success_response("Request details", {
        "id": r[0], "chain_id": r[1], "source_module": r[2], "source_id": r[3],
        "title": r[4], "description": r[5], "requested_by": r[6],
        "current_step": r[7], "status": r[8],
        "created_at": str(r[9]) if r[9] else None,
        "updated_at": str(r[10]) if r[10] else None,
        "completed_at": str(r[11]) if r[11] else None,
        "actions": [{"step_order": a[0], "approver_id": a[1], "decision": a[2],
                     "comment": a[3], "decided_at": str(a[4]) if a[4] else None} for a in actions],
        "chain_steps": [{"step_order": s[0], "step_name": s[1], "approver_type": s[2],
                         "approver_value": s[3], "min_approvals": s[4], "is_optional": s[5]} for s in steps],
    })


# ═══════════════════════════════════════════════════
# DECISIONS
# ═══════════════════════════════════════════════════

class DecisionBody(BaseModel):
    decision: str
    comment: str | None = None

@router.post("/requests/{request_id}/decide")
def make_decision(request_id: str, body: DecisionBody, user: dict | None=None, db=Depends(get_db)):
    if body.decision not in ("approved", "rejected", "escalated", "delegated"):
        raise HTTPException(400, detail="Invalid decision. Must be: approved, rejected, escalated, delegated")
    t = user["tenant_id"]
    uid_ = user["id"]
    req = db.execute(text(
        "SELECT id,chain_id,current_step,status FROM dbp_approve_requests WHERE id=:id AND tenant_id=:t"),
        {"id": request_id, "t": t}).fetchone()
    if not req:
        raise HTTPException(404, detail="Request not found")
    if req[3] != "pending":
        raise HTTPException(400, detail=f"Request is already {req[3]}")
    aid = uid()
    db.execute(text("INSERT INTO dbp_approve_actions (id,tenant_id,request_id,step_order,approver_id,decision,comment) "
                    "VALUES (:id,:t,:rid,:so,:ai,:d,:c)"),
               {"id": aid, "t": t, "rid": request_id, "so": req[2], "ai": uid_,
                "d": body.decision, "c": body.comment})
    _log_action(db, t, request_id, f"decision_{body.decision}", uid_, body.comment or f"Decided: {body.decision}")

    if body.decision == "rejected":
        db.execute(text("UPDATE dbp_approve_requests SET status='rejected', updated_at=NOW() WHERE id=:id"),
                   {"id": request_id})
        audit_log(db, t, uid_, "reject", "approve_request", request_id)
    elif body.decision == "approved":
        chain_id = req[1]
        current_step = req[2]
        steps = db.execute(text(
            "SELECT step_order,min_approvals FROM dbp_approve_steps WHERE chain_id=:cid AND tenant_id=:t ORDER BY step_order"),
            {"cid": chain_id, "t": t}).fetchall()
        approvals_at_step = db.execute(text(
            "SELECT COUNT(*) FROM dbp_approve_actions WHERE request_id=:rid AND step_order=:so AND decision='approved'"),
            {"rid": request_id, "so": current_step}).fetchone()[0] or 0
        current_step_def = None
        for s in steps:
            if s[0] == current_step:
                current_step_def = s
                break
        if current_step_def and approvals_at_step >= current_step_def[1]:
            next_step = current_step + 1
            has_next = any(s[0] == next_step for s in steps)
            if has_next:
                db.execute(text("UPDATE dbp_approve_requests SET current_step=:ns, updated_at=NOW() WHERE id=:id"),
                           {"ns": next_step, "id": request_id})
                _log_action(db, t, request_id, "step_advanced", uid_, f"Advanced to step {next_step}")
            else:
                db.execute(text("UPDATE dbp_approve_requests SET status='approved', updated_at=NOW(), completed_at=NOW() WHERE id=:id"),
                           {"id": request_id})
                _log_action(db, t, request_id, "approved", uid_, "All steps completed — approved")
                audit_log(db, t, uid_, "approve", "approve_request", request_id)
    db.commit()
    return success_response("Decision recorded", {"id": aid, "decision": body.decision})

@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    req = db.execute(text(
        "SELECT id,status,requested_by FROM dbp_approve_requests WHERE id=:id AND tenant_id=:t"),
        {"id": request_id, "t": t}).fetchone()
    if not req:
        raise HTTPException(404, detail="Request not found")
    if req[1] != "pending":
        raise HTTPException(400, detail=f"Request is already {req[1]}")
    if req[2] != user["id"]:
        raise HTTPException(403, detail="Only the requester can cancel")
    db.execute(text("UPDATE dbp_approve_requests SET status='cancelled', updated_at=NOW() WHERE id=:id"),
               {"id": request_id})
    _log_action(db, t, request_id, "cancelled", user["id"], "Cancelled by requester")
    db.commit()
    return success_response("Request cancelled", {"id": request_id})


# ═══════════════════════════════════════════════════
# QUICK APPROVE (simplified: approve without chain)
# ═══════════════════════════════════════════════════

@router.get("/pending")
def pending_for_user(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    user["id"]
    rows = db.execute(text(
        "SELECT r.id,r.source_module,r.source_id,r.title,r.requested_by,r.current_step,r.created_at "
        "FROM dbp_approve_requests r WHERE r.tenant_id=:t AND r.status='pending' ORDER BY r.created_at DESC LIMIT 50"),
        {"t": t}).fetchall()
    data = [{"id": r[0], "source_module": r[1], "source_id": r[2], "title": r[3],
             "requested_by": r[4], "current_step": r[5],
             "created_at": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))

@router.get("/stats")
def approval_stats(user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    pending = db.execute(text("SELECT COUNT(*) FROM dbp_approve_requests WHERE tenant_id=:t AND status='pending'"), {"t": t}).fetchone()[0] or 0
    approved = db.execute(text("SELECT COUNT(*) FROM dbp_approve_requests WHERE tenant_id=:t AND status='approved'"), {"t": t}).fetchone()[0] or 0
    rejected = db.execute(text("SELECT COUNT(*) FROM dbp_approve_requests WHERE tenant_id=:t AND status='rejected'"), {"t": t}).fetchone()[0] or 0
    total = pending + approved + rejected
    return success_response("Approval stats", {"pending": pending, "approved": approved, "rejected": rejected, "total": total})

@router.get("/log/{request_id}")
def get_log(request_id: str, user: dict | None=None, db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT action,actor_id,details,created_at FROM dbp_approve_log WHERE request_id=:rid AND tenant_id=:t ORDER BY created_at"),
        {"rid": request_id, "t": t}).fetchall()
    data = [{"action": r[0], "actor_id": r[1], "details": r[2],
             "created_at": str(r[3]) if r[3] else None} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _log_action(db, tenant_id, request_id, action, actor_id, details):
    lid = uid()
    db.execute(text("INSERT INTO dbp_approve_log (id,tenant_id,request_id,action,actor_id,details) "
                    "VALUES (:id,:t,:rid,:a,:ai,:d)"),
               {"id": lid, "t": tenant_id, "rid": request_id, "a": action, "ai": actor_id, "d": details})
