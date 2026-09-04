"""
P15 Notification Router — CRUD + preferences + mark read
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.notification_engine import NotificationEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Notifications"])


@router.get("/notifications", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_notifications(is_read: bool | None = None, notification_type: str | None = None, channel: str | None = None, entity_code: str | None = None, limit: int | None=None, offset: int = Query(0, ge=0), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.get("id") or user.get("user_id"); tenant_id = user.get("tenant_id")
    conditions = ["user_id = :uid"]; params: dict = {"uid": user_id, "limit": limit, "offset": offset}
    if tenant_id: conditions.append("tenant_id = :tid"); params["tid"] = tenant_id
    if is_read is not None: conditions.append("is_read = :is_read"); params["is_read"] = is_read
    if notification_type: conditions.append("notification_type = :nt"); params["nt"] = notification_type
    if channel: conditions.append("channel = :ch"); params["ch"] = channel
    if entity_code: conditions.append("entity_code = :ec"); params["ec"] = entity_code
    where = " AND ".join(conditions)
    rows = db.execute(text(f"SELECT id, tenant_id, user_id, channel, title, message, notification_type, entity_code, record_id, event_id, action_url, is_read, read_at, created_at FROM dbp_notifications WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"), params).fetchall()
    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_notifications WHERE {where}"), params).fetchone()
    notifications = [{"id":r[0],"tenant_id":r[1],"user_id":r[2],"channel":r[3],"title":r[4],"message":r[5],"notification_type":r[6],"entity_code":r[7],"record_id":r[8],"event_id":r[9],"action_url":r[10],"is_read":bool(r[11]),"read_at":r[12].isoformat() if r[12] else None,"created_at":r[13].isoformat() if r[13] else None} for r in rows]
    return {"status":"success","data":notifications,"meta":{"count":count_row[0],"limit":limit,"offset":offset}}


@router.get("/notifications/{notification_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_notification(notification_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    user_id = user.get("id") or user.get("user_id")
    row = db.execute(text("SELECT id, tenant_id, user_id, channel, title, message, notification_type, entity_code, record_id, event_id, action_url, is_read, read_at, extra_data, created_at FROM dbp_notifications WHERE id = :id"), {"id":notification_id}).fetchone()
    if not row: raise HTTPException(status_code=404, detail={"status":"error","error":{"code":"NOT_FOUND","message":"Notification not found"}})
    if row[2] != user_id: raise HTTPException(status_code=403, detail={"status":"error","error":{"code":"FORBIDDEN","message":"Not your notification"}})
    return {"status":"success","data":{"id":row[0],"tenant_id":row[1],"user_id":row[2],"channel":row[3],"title":row[4],"message":row[5],"notification_type":row[6],"entity_code":row[7],"record_id":row[8],"event_id":row[9],"action_url":row[10],"is_read":bool(row[11]),"read_at":row[12].isoformat() if row[12] else None,"metadata":row[13],"created_at":row[14].isoformat() if row[14] else None}}


@router.post("/notifications/{notification_id}/read", dependencies=[Depends(require_permission("dynamic", "read")), Depends(write_limiter.check)])
async def mark_notification_read(notification_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    ok = NotificationEngine(db).mark_read(notification_id, user.get("id") or user.get("user_id"))
    if not ok: raise HTTPException(status_code=404, detail={"status":"error","error":{"code":"NOT_FOUND","message":"Notification not found or not yours"}})
    return {"status":"success","message":"Marked as read"}


@router.post("/notifications/read-all", dependencies=[Depends(require_permission("dynamic", "read")), Depends(write_limiter.check)])
async def mark_all_notifications_read(user: dict | None=None, db: Session = Depends(get_db)):
    count = NotificationEngine(db).mark_all_read(user.get("id") or user.get("user_id"), user.get("tenant_id"))
    return {"status":"success","marked_read":count}


@router.get("/notifications-count", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def notifications_count(user: dict | None=None, db: Session = Depends(get_db)):
    user_id=user.get("id") or user.get("user_id"); tenant_id=user.get("tenant_id"); conditions=["user_id = :uid","is_read = false"]; params={"uid":user_id}
    if tenant_id: conditions.append("tenant_id = :tid"); params["tid"]=tenant_id
    row=db.execute(text(f"SELECT COUNT(*) FROM dbp_notifications WHERE {' AND '.join(conditions)}"),params).fetchone()
    return {"status":"success","data":{"unread_count":row[0]}}


@router.delete("/notifications/{notification_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(write_limiter.check)])
async def delete_notification(notification_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    result=db.execute(text("DELETE FROM dbp_notifications WHERE id = :id AND user_id = :uid"),{"id":notification_id,"uid":user.get("id") or user.get("user_id")}); db.commit()
    if result.rowcount == 0: raise HTTPException(status_code=404, detail={"status":"error","error":{"code":"NOT_FOUND","message":"Notification not found or not yours"}})
    return {"status":"success","message":"Notification deleted"}


@router.get("/notification-preferences", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_notification_preferences(user: dict | None=None, db: Session = Depends(get_db)):
    rows=db.execute(text("SELECT id, notification_type, channel, is_enabled FROM dbp_notification_preferences WHERE user_id = :uid ORDER BY notification_type, channel"),{"uid":user.get("id") or user.get("user_id")}).fetchall()
    return {"status":"success","data":[{"id":r[0],"notification_type":r[1],"channel":r[2],"is_enabled":bool(r[3])} for r in rows]}


@router.put("/notification-preferences", dependencies=[Depends(require_permission("dynamic", "read")), Depends(write_limiter.check)])
async def update_notification_preference(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    user_id=user.get("id") or user.get("user_id"); tenant_id=user.get("tenant_id"); ntype=body.get("notification_type"); channel=body.get("channel","in_app"); is_enabled=body.get("is_enabled",True)
    if not ntype: raise HTTPException(status_code=400,detail={"status":"error","error":{"code":"MISSING_FIELD","message":"notification_type required"}})
    existing=db.execute(text("SELECT id FROM dbp_notification_preferences WHERE user_id = :uid AND notification_type = :nt AND channel = :ch"),{"uid":user_id,"nt":ntype,"ch":channel}).fetchone()
    if existing:
        db.execute(text("UPDATE dbp_notification_preferences SET is_enabled = :ie WHERE id = :id"),{"id":existing[0],"ie":is_enabled})
    else:
        db.execute(text("INSERT INTO dbp_notification_preferences (id, tenant_id, user_id, notification_type, channel, is_enabled) VALUES (:id, :tid, :uid, :nt, :ch, :ie)"),{"id":str(uuid.uuid4()),"tid":tenant_id,"uid":user_id,"nt":ntype,"ch":channel,"ie":is_enabled})
    db.commit(); return {"status":"success","message":"Preference updated"}


@router.get("/notification-templates", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_notification_templates(db: Session = Depends(get_db)):
    rows=db.execute(text("SELECT id, code, channel, notification_type, title_template, message_template, event_type, is_active FROM dbp_notification_templates ORDER BY code")).fetchall()
    return {"status":"success","data":[{"id":r[0],"code":r[1],"channel":r[2],"notification_type":r[3],"title_template":r[4],"message_template":r[5],"event_type":r[6],"is_active":bool(r[7])} for r in rows]}


@router.put("/notification-templates/{template_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_notification_template(template_id: str, body: dict, db: Session = Depends(get_db)):
    existing=db.execute(text("SELECT id FROM dbp_notification_templates WHERE id = :id"),{"id":template_id}).fetchone()
    if not existing: raise HTTPException(status_code=404,detail={"status":"error","error":{"code":"NOT_FOUND","message":"Template not found"}})
    updates=[]; params={"id":template_id}
    for field in ("title_template","message_template","notification_type","is_active"):
        if field in body: updates.append(f"{field} = :{field}"); params[field]=body[field]
    if updates: db.execute(text(f"UPDATE dbp_notification_templates SET {', '.join(updates)} WHERE id = :id"),params); db.commit()
    return {"status":"success","message":"Template updated"}
