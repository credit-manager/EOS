from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.tenant_lifecycle import TenantLifecycleEngine
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/tenant-lifecycle", tags=["Tenant Lifecycle"])


# ------------------------------------------------ lifecycle events
@router.get("/events",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_events(event_type: str | None = None, limit: int = 50,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).list_events(
        user["tenant_id"], event_type=event_type, limit=limit)
    return {"status": "success", "data": data}


@router.post("/events",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_event(body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    required = ["event_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eid = TenantLifecycleEngine(db).record_event(
        user["tenant_id"], body["event_type"],
        event_data=body.get("event_data"),
        actor_id=user.get("user_id"),
        actor_email=user.get("email"),
        reason=body.get("reason"))
    db.commit()
    return {"status": "success", "data": {"id": eid, "message": "Event recorded"}}


@router.get("/events/{event_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_event(event_id: str,
                   user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).get_event(user["tenant_id"], event_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Event not found"}})
    return {"status": "success", "data": data}


# ----------------------------------------------------- data exports
@router.get("/data-exports",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_data_exports(status: str | None = None,
                           user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).list_data_exports(
        user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/data-exports",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_data_export(body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    required = ["export_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eid = TenantLifecycleEngine(db).create_data_export(
        user["tenant_id"], body["export_type"],
        entity_types=body.get("entity_types"),
        requested_by=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": eid, "message": "Data export started"}}


@router.put("/data-exports/{export_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_data_export(export_id: str, body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    result = TenantLifecycleEngine(db).update_data_export(
        user["tenant_id"], export_id, body.get("status", "completed"),
        file_path=body.get("file_path"),
        file_size_bytes=body.get("file_size_bytes"),
        record_count=body.get("record_count"))
    db.commit()
    return {"status": "success", "data": result}


# ----------------------------------------------------- invitations
@router.get("/invitations",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_invitations(status: str | None = None,
                          user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).list_invitations(
        user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/invitations",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_invitation(body: dict,
                           user: dict | None=None, db: Session = Depends(get_db)):
    required = ["email", "role"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    iid = TenantLifecycleEngine(db).create_invitation(
        user["tenant_id"], body["email"], body["role"],
        invited_by=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": iid, "message": "Invitation sent"}}


@router.put("/invitations/{invitation_id}/accept",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def accept_invitation(invitation_id: str,
                           user: dict | None=None, db: Session = Depends(get_db)):
    result = TenantLifecycleEngine(db).accept_invitation(
        user["tenant_id"], invitation_id)
    db.commit()
    return {"status": "success", "data": result}


@router.put("/invitations/{invitation_id}/revoke",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def revoke_invitation(invitation_id: str,
                           user: dict | None=None, db: Session = Depends(get_db)):
    result = TenantLifecycleEngine(db).revoke_invitation(
        user["tenant_id"], invitation_id)
    db.commit()
    return {"status": "success", "data": result}


# ----------------------------------------------------- activity logs
@router.get("/activity-logs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_activity_logs(action: str | None = None, resource_type: str | None = None, limit: int = 50,
                            user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).list_activity_logs(
        user["tenant_id"], action=action, resource_type=resource_type, limit=limit)
    return {"status": "success", "data": data}


@router.post("/activity-logs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def log_activity(body: dict,
                      user: dict | None=None, db: Session = Depends(get_db)):
    required = ["action"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = TenantLifecycleEngine(db).log_activity(
        user["tenant_id"], body["action"],
        user_id=user.get("user_id"),
        resource_type=body.get("resource_type"),
        resource_id=body.get("resource_id"),
        details=body.get("details"),
        ip_address=body.get("ip_address"))
    db.commit()
    return {"status": "success", "data": {"id": lid, "message": "Activity logged"}}


# --------------------------------------------------- notifications
@router.get("/notifications",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_notifications(is_read: bool | None = None, severity: str | None = None, limit: int = 50,
                            user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).list_notifications(
        user["tenant_id"], is_read=is_read, severity=severity, limit=limit)
    return {"status": "success", "data": data}


@router.post("/notifications",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_notification(body: dict,
                             user: dict | None=None, db: Session = Depends(get_db)):
    required = ["notification_type", "title"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    nid = TenantLifecycleEngine(db).create_notification(
        user["tenant_id"], body["notification_type"], body["title"],
        message=body.get("message"), severity=body.get("severity", "info"),
        action_url=body.get("action_url"))
    db.commit()
    return {"status": "success", "data": {"id": nid, "message": "Notification created"}}


@router.get("/notifications/{notification_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_notification(notification_id: str,
                          user: dict | None=None, db: Session = Depends(get_db)):
    data = TenantLifecycleEngine(db).get_notification(user["tenant_id"], notification_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Notification not found"}})
    return {"status": "success", "data": data}


@router.put("/notifications/{notification_id}/read",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def mark_notification_read(notification_id: str,
                                user: dict | None=None, db: Session = Depends(get_db)):
    result = TenantLifecycleEngine(db).mark_notification_read(
        user["tenant_id"], notification_id)
    db.commit()
    return {"status": "success", "data": result}


@router.delete("/notifications/{notification_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_notification(notification_id: str,
                             user: dict | None=None, db: Session = Depends(get_db)):
    result = TenantLifecycleEngine(db).delete_notification(
        user["tenant_id"], notification_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Notification not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}
