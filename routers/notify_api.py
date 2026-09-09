"""
P71.1 Shared Notification Engine — API
========================================
Event-driven notification system. Fire events → match rules → deliver.
Shared across all 6 industries.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from database import SessionLocal, get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import (
    now, uid, check_permission, audit_log,
    success_response, list_response,
)

router = APIRouter(prefix="/notifications", tags=["Notification Engine"])


# ═══════════════════════════════════════════════════
# CORE: FIRE EVENT
# ═══════════════════════════════════════════════════

class EventFire(BaseModel):
    event_type: str
    source_module: str
    source_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

@router.post("/events/fire")
def fire_event(body: EventFire, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    eid = uid()
    payload_json = json.dumps(body.payload) if body.payload else None
    db.execute(text("INSERT INTO dbp_notify_events (id,tenant_id,event_type,source_module,source_id,payload) "
                    "VALUES (:id,:t,:et,:sm,:si,:pl)"),
               {"id": eid, "t": t, "et": body.event_type, "sm": body.source_module,
                "si": body.source_id, "pl": payload_json})

    rules = db.execute(text(
        "SELECT id,channel,recipient_type,recipient_value,template_id,rule_name "
        "FROM dbp_notify_rules WHERE tenant_id=:t AND event_type=:et AND is_active=TRUE ORDER BY priority"),
        {"t": t, "et": body.event_type}).fetchall()

    delivered = 0
    for rule in rules:
        rule_id, channel, recip_type, recip_val, template_id, rule_name = rule

        try:
            recipients = _resolve_recipients(db, t, recip_type, recip_val, user["id"], body.payload)
        except Exception:
            recipients = [user["id"]]

        template_subject = ""
        template_body = ""
        if template_id:
            try:
                tmpl = db.execute(text("SELECT subject,body FROM dbp_notify_templates WHERE id=:tid AND tenant_id=:t"),
                                  {"tid": template_id, "t": t}).fetchone()
                if tmpl:
                    template_subject = _render(tmpl[0], body.payload or {})
                    template_body = _render(tmpl[1], body.payload or {})
            except Exception:
                pass
        else:
            template_subject = f"{body.event_type} — {body.source_module}"
            template_body = json.dumps(body.payload or {}, default=str)[:500]

        for recipient_id in recipients:
            try:
                if channel == "in_app":
                    nid = uid()
                    db.execute(text(
                        "INSERT INTO dbp_notify_inbox (id,tenant_id,user_id,event_id,title,body,link,category) "
                        "VALUES (:id,:t,:uid,:eid,:title,:body,:link,:cat)"),
                        {"id": nid, "t": t, "uid": recipient_id, "eid": eid,
                         "title": template_subject, "body": template_body,
                         "link": f"/{body.source_module}/{body.source_id}" if body.source_id else None,
                         "cat": _event_category(body.event_type)})
                    delivered += 1
                elif channel == "email":
                    _queue_email(db, t, recipient_id, template_subject, template_body)
            except Exception:
                pass

    audit_log(db, t, user["id"], "fire", "notification_event", eid,
              new_values={"event_type": body.event_type, "rules_matched": len(rules), "delivered": delivered})
    db.commit()
    return success_response("Event fired", {
        "event_id": eid, "rules_matched": len(rules), "delivered": delivered
    })


def _resolve_recipients(db, tenant_id, recip_type, recip_val, fired_by, payload):
    if recip_type == "user" and recip_val:
        return [recip_val]
    elif recip_type == "role" and recip_val:
        rows = db.execute(text("SELECT id FROM users WHERE tenant_id=:t AND role LIKE :r"),
                          {"t": tenant_id, "r": f"%{recip_val}%"}).fetchall()
        if rows:
            return [r[0] for r in rows]
        return [fired_by]
    elif recip_type == "manager":
        return [fired_by]
    elif recip_type == "assigned":
        if payload and "assigned_to" in payload:
            return [payload["assigned_to"]]
        return [fired_by]
    elif recip_type == "all":
        rows = db.execute(text("SELECT id FROM users WHERE tenant_id=:t"), {"t": tenant_id}).fetchall()
        if rows:
            return [r[0] for r in rows]
        return [fired_by]
    return [fired_by]


def _render(template, variables):
    if not template:
        return ""
    result = template
    for key, value in (variables or {}).items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def _event_category(event_type):
    if "approve" in event_type.lower():
        return "approval"
    if "task" in event_type.lower():
        return "task"
    if "error" in event_type.lower() or "fail" in event_type.lower():
        return "error"
    if "complete" in event_type.lower() or "success" in event_type.lower():
        return "success"
    if "overdue" in event_type.lower() or "alert" in event_type.lower():
        return "warning"
    return "info"


def _queue_email(db, tenant_id, recipient_id, subject, body):
    pass  # Future: email queue integration


# ═══════════════════════════════════════════════════
# INBOX
# ═══════════════════════════════════════════════════

@router.get("/inbox")
def list_inbox(unread_only: bool = False, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    uid_ = user["id"]
    where = "WHERE tenant_id=:t AND user_id=:u"
    params = {"t": t, "u": uid_}
    if unread_only:
        where += " AND is_read=FALSE"
    rows = db.execute(text(
        f"SELECT id,title,body,link,category,is_read,created_at "
        f"FROM dbp_notify_inbox {where} ORDER BY created_at DESC LIMIT 100"), params).fetchall()
    data = [{"id": r[0], "title": r[1], "body": r[2], "link": r[3], "category": r[4],
             "is_read": r[5], "created_at": str(r[6]) if r[6] else None} for r in rows]
    return list_response(data, len(data))

@router.get("/inbox/count")
def inbox_count(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    uid_ = user["id"]
    total = db.execute(text("SELECT COUNT(*) FROM dbp_notify_inbox WHERE tenant_id=:t AND user_id=:u"), {"t": t, "u": uid_}).fetchone()[0] or 0
    unread = db.execute(text("SELECT COUNT(*) FROM dbp_notify_inbox WHERE tenant_id=:t AND user_id=:u AND is_read=FALSE"), {"t": t, "u": uid_}).fetchone()[0] or 0
    return success_response("Inbox count", {"total": total, "unread": unread})

@router.put("/inbox/{notif_id}/read")
def mark_read(notif_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    db.execute(text("UPDATE dbp_notify_inbox SET is_read=TRUE, read_at=NOW() WHERE id=:id AND tenant_id=:t AND user_id=:u"),
               {"id": notif_id, "t": t, "u": user["id"]})
    db.commit()
    return success_response("Marked as read", {"id": notif_id})

@router.put("/inbox/read-all")
def mark_all_read(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    uid_ = user["id"]
    count = db.execute(text("UPDATE dbp_notify_inbox SET is_read=TRUE, read_at=NOW() "
                            "WHERE tenant_id=:t AND user_id=:u AND is_read=FALSE"),
                       {"t": t, "u": uid_}).rowcount
    db.commit()
    return success_response("All marked as read", {"count": count})


# ═══════════════════════════════════════════════════
# RULES
# ═══════════════════════════════════════════════════

class RuleCreate(BaseModel):
    rule_name: str
    event_type: str
    source_module: Optional[str] = None
    channel: str = "in_app"
    recipient_type: str = "user"
    recipient_value: Optional[str] = None
    template_id: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    conditions: Optional[Dict[str, Any]] = None

@router.post("/rules")
def create_rule(body: RuleCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    valid_channels = {"in_app", "email", "sms", "whatsapp"}
    if body.channel not in valid_channels:
        raise HTTPException(400, detail=f"Invalid channel. Must be one of: {valid_channels}")
    valid_recipients = {"user", "role", "manager", "all", "assigned"}
    if body.recipient_type not in valid_recipients:
        raise HTTPException(400, detail=f"Invalid recipient_type. Must be one of: {valid_recipients}")
    existing = db.execute(text("SELECT id FROM dbp_notify_rules WHERE tenant_id=:t AND rule_name=:rn"),
                          {"t": t, "rn": body.rule_name}).fetchone()
    if existing:
        raise HTTPException(400, detail="Rule name already exists")
    rid = uid()
    cond_json = json.dumps(body.conditions) if body.conditions else None
    db.execute(text("INSERT INTO dbp_notify_rules "
                    "(id,tenant_id,rule_name,event_type,source_module,channel,recipient_type,recipient_value,template_id,priority,conditions) "
                    "VALUES (:id,:t,:rn,:et,:sm,:ch,:rt,:rv,:tp,:pr,:co)"),
               {"id": rid, "t": t, "rn": body.rule_name, "et": body.event_type,
                "sm": body.source_module, "ch": body.channel, "rt": body.recipient_type,
                "rv": body.recipient_value, "tp": body.template_id, "pr": body.priority, "co": cond_json})
    audit_log(db, t, user["id"], "create", "notify_rule", rid, new_values={"rule_name": body.rule_name})
    db.commit()
    return success_response("Rule created", {"id": rid})

@router.get("/rules")
def list_rules(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,rule_name,event_type,source_module,channel,recipient_type,recipient_value,is_active,priority "
        "FROM dbp_notify_rules WHERE tenant_id=:t ORDER BY priority"), {"t": t}).fetchall()
    data = [{"id": r[0], "rule_name": r[1], "event_type": r[2], "source_module": r[3],
             "channel": r[4], "recipient_type": r[5], "recipient_value": r[6],
             "is_active": r[7], "priority": r[8]} for r in rows]
    return list_response(data, len(data))

@router.put("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "update")
    t = user["tenant_id"]
    r = db.execute(text("SELECT is_active FROM dbp_notify_rules WHERE id=:id AND tenant_id=:t"),
                   {"id": rule_id, "t": t}).fetchone()
    if not r:
        raise HTTPException(404, detail="Rule not found")
    new_val = not r[0]
    db.execute(text("UPDATE dbp_notify_rules SET is_active=:v, updated_at=NOW() WHERE id=:id"),
               {"v": new_val, "id": rule_id})
    db.commit()
    return success_response("Rule toggled", {"is_active": new_val})


# ═══════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════

class TemplateCreate(BaseModel):
    template_code: str
    name: str
    channel: str = "in_app"
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None
    variables: Optional[List[str]] = None

@router.post("/templates")
def create_template(body: TemplateCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    check_permission(user, "create")
    t = user["tenant_id"]
    existing = db.execute(text("SELECT id FROM dbp_notify_templates WHERE tenant_id=:t AND template_code=:tc"),
                          {"t": t, "tc": body.template_code}).fetchone()
    if existing:
        raise HTTPException(400, detail="Template code already exists")
    tid = uid()
    vars_json = json.dumps(body.variables) if body.variables else None
    db.execute(text("INSERT INTO dbp_notify_templates "
                    "(id,tenant_id,template_code,name,channel,subject,body,body_html,variables) "
                    "VALUES (:id,:t,:tc,:n,:ch,:s,:b,:bh,:v)"),
               {"id": tid, "t": t, "tc": body.template_code, "n": body.name,
                "ch": body.channel, "s": body.subject, "b": body.body,
                "bh": body.body_html, "v": vars_json})
    audit_log(db, t, user["id"], "create", "notify_template", tid, new_values={"template_code": body.template_code})
    db.commit()
    return success_response("Template created", {"id": tid})

@router.get("/templates")
def list_templates(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT id,template_code,name,channel,subject,is_active "
        "FROM dbp_notify_templates WHERE tenant_id=:t ORDER BY template_code"), {"t": t}).fetchall()
    data = [{"id": r[0], "template_code": r[1], "name": r[2], "channel": r[3],
             "subject": r[4], "is_active": r[5]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# PREFERENCES
# ═══════════════════════════════════════════════════

class PrefUpdate(BaseModel):
    category: str
    in_app: bool = True
    email: bool = False
    is_muted: bool = False

@router.post("/preferences")
def update_preferences(body: PrefUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    pid = uid()
    db.execute(text(
        "INSERT INTO dbp_notify_preferences (id,tenant_id,user_id,category,in_app,email,is_muted) "
        "VALUES (:id,:t,:u,:c,:ia,:e,:m) ON CONFLICT (tenant_id,user_id,category) "
        "DO UPDATE SET in_app=:ia, email=:e, is_muted=:m"),
        {"id": pid, "t": t, "u": user["id"], "c": body.category,
         "ia": body.in_app, "e": body.email, "m": body.is_muted})
    db.commit()
    return success_response("Preferences updated", {"category": body.category})

@router.get("/preferences")
def list_preferences(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    rows = db.execute(text(
        "SELECT category,in_app,email,is_muted FROM dbp_notify_preferences WHERE tenant_id=:t AND user_id=:u"),
        {"t": t, "u": user["id"]}).fetchall()
    data = [{"category": r[0], "in_app": r[1], "email": r[2], "is_muted": r[3]} for r in rows]
    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════

@router.get("/stats")
def notification_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    events_today = db.execute(text(
        "SELECT COUNT(*) FROM dbp_notify_events WHERE tenant_id=:t AND created_at >= CURRENT_DATE"),
        {"t": t}).fetchone()[0] or 0
    total_inbox = db.execute(text(
        "SELECT COUNT(*) FROM dbp_notify_inbox WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    unread = db.execute(text(
        "SELECT COUNT(*) FROM dbp_notify_inbox WHERE tenant_id=:t AND is_read=FALSE"),
        {"t": t}).fetchone()[0] or 0
    rules_active = db.execute(text(
        "SELECT COUNT(*) FROM dbp_notify_rules WHERE tenant_id=:t AND is_active=TRUE"),
        {"t": t}).fetchone()[0] or 0
    templates = db.execute(text(
        "SELECT COUNT(*) FROM dbp_notify_templates WHERE tenant_id=:t"),
        {"t": t}).fetchone()[0] or 0
    return success_response("Notification stats", {
        "events_today": events_today, "total_inbox": total_inbox,
        "unread": unread, "rules_active": rules_active, "templates": templates
    })
