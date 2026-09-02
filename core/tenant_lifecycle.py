"""
P42 Tenant Lifecycle Engine
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class TenantLifecycleEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------- lifecycle events
    def record_event(self, tenant_id, event_type, event_data=None,
                     actor_id=None, actor_email=None, reason=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_lifecycle_events "
            "(id, tenant_id, event_type, event_data, actor_id, actor_email, reason, created_at) "
            "VALUES (:id,:tid,:et,:ed,:ai,:ae,:re,NOW())"
        ), {"id": eid, "tid": tenant_id, "et": event_type,
            "ed": __import__('json').dumps(event_data) if event_data else None,
            "ai": actor_id, "ae": actor_email, "re": reason})
        return eid

    def list_events(self, tenant_id, event_type=None, limit=50):
        q = "SELECT id, tenant_id, event_type, event_data, actor_id, actor_email, reason, created_at FROM dbp_tenant_lifecycle_events WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if event_type:
            q += " AND event_type=:et"
            params["et"] = event_type
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "event_type": r[2],
                 "event_data": r[3], "actor_id": r[4], "actor_email": r[5],
                 "reason": r[6], "created_at": str(r[7]) if r[7] else None} for r in rows]

    def get_event(self, tenant_id, event_id):
        r = self.db.execute(text(
            "SELECT id, tenant_id, event_type, event_data, actor_id, actor_email, reason, created_at "
            "FROM dbp_tenant_lifecycle_events WHERE id=:id AND tenant_id=:tid"
        ), {"id": event_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "tenant_id": r[1], "event_type": r[2],
                "event_data": r[3], "actor_id": r[4], "actor_email": r[5],
                "reason": r[6], "created_at": str(r[7]) if r[7] else None}

    # ----------------------------------------------------- data exports
    def create_data_export(self, tenant_id, export_type, entity_types=None,
                           requested_by=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_data_exports "
            "(id, tenant_id, export_type, entity_types, status, requested_by, created_at) "
            "VALUES (:id,:tid,:et,:et2,'pending',:rb,NOW())"
        ), {"id": eid, "tid": tenant_id, "et": export_type,
            "et2": __import__('json').dumps(entity_types) if entity_types else None,
            "rb": requested_by})
        return eid

    def update_data_export(self, tenant_id, export_id, status, file_path=None,
                           file_size_bytes=None, record_count=None):
        sets = ["status=:st"]
        params: dict[str, Any] = {"id": export_id, "tid": tenant_id, "st": status}
        if file_path:
            sets.append("file_path=:fp")
            params["fp"] = file_path
        if file_size_bytes is not None:
            sets.append("file_size_bytes=:fs")
            params["fs"] = file_size_bytes
        if record_count is not None:
            sets.append("record_count=:rc")
            params["rc"] = record_count
        if status == "running":
            sets.append("started_at=NOW()")
        elif status in ("completed", "failed"):
            sets.append("completed_at=NOW()")
        self.db.execute(text(
            f"UPDATE dbp_tenant_data_exports SET {', '.join(sets)} WHERE id=:id AND tenant_id=:tid"
        ), params)
        return {"id": export_id, "status": status}

    def list_data_exports(self, tenant_id, status=None, limit=20):
        q = "SELECT id, export_type, entity_types, status, file_path, file_size_bytes, record_count, requested_by, started_at, completed_at, created_at FROM dbp_tenant_data_exports WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "export_type": r[1], "entity_types": r[2],
                 "status": r[3], "file_path": r[4], "file_size_bytes": r[5],
                 "record_count": r[6], "requested_by": r[7],
                 "started_at": str(r[8]) if r[8] else None,
                 "completed_at": str(r[9]) if r[9] else None,
                 "created_at": str(r[10]) if r[10] else None} for r in rows]

    # ----------------------------------------------------- invitations
    def create_invitation(self, tenant_id, email, role, invited_by=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_invitations "
            "(id, tenant_id, email, role, status, invited_by, created_at) "
            "VALUES (:id,:tid,:em,:ro,'pending',:ib,NOW())"
        ), {"id": eid, "tid": tenant_id, "em": email, "ro": role, "ib": invited_by})
        return eid

    def accept_invitation(self, tenant_id, invitation_id):
        self.db.execute(text(
            "UPDATE dbp_tenant_invitations SET status='accepted', accepted_at=NOW() "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"id": invitation_id, "tid": tenant_id})
        return {"id": invitation_id, "status": "accepted"}

    def revoke_invitation(self, tenant_id, invitation_id):
        self.db.execute(text(
            "UPDATE dbp_tenant_invitations SET status='revoked' "
            "WHERE id=:id AND tenant_id=:tid"
        ), {"id": invitation_id, "tid": tenant_id})
        return {"id": invitation_id, "status": "revoked"}

    def list_invitations(self, tenant_id, status=None, limit=50):
        q = "SELECT id, email, role, status, invited_by, accepted_at, created_at FROM dbp_tenant_invitations WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if status:
            q += " AND status=:st"
            params["st"] = status
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "email": r[1], "role": r[2],
                 "status": r[3], "invited_by": r[4],
                 "accepted_at": str(r[5]) if r[5] else None,
                 "created_at": str(r[6]) if r[6] else None} for r in rows]

    # ----------------------------------------------------- activity logs
    def log_activity(self, tenant_id, action, user_id=None, resource_type=None,
                     resource_id=None, details=None, ip_address=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_activity_logs "
            "(id, tenant_id, user_id, action, resource_type, resource_id, details, ip_address, created_at) "
            "VALUES (:id,:tid,:ui,:ac,:rt,:ri,:de,:ip,NOW())"
        ), {"id": eid, "tid": tenant_id, "ui": user_id, "ac": action,
            "rt": resource_type, "ri": resource_id,
            "de": __import__('json').dumps(details) if details else None,
            "ip": ip_address})
        return eid

    def list_activity_logs(self, tenant_id, action=None, resource_type=None, limit=50):
        q = "SELECT id, tenant_id, user_id, action, resource_type, resource_id, details, ip_address, created_at FROM dbp_tenant_activity_logs WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if action:
            q += " AND action=:ac"
            params["ac"] = action
        if resource_type:
            q += " AND resource_type=:rt"
            params["rt"] = resource_type
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "user_id": r[2],
                 "action": r[3], "resource_type": r[4],
                 "resource_id": r[5], "details": r[6],
                 "ip_address": r[7],
                 "created_at": str(r[8]) if r[8] else None} for r in rows]

    # --------------------------------------------------- notifications
    def create_notification(self, tenant_id, notification_type, title, message=None,
                            severity="info", action_url=None):
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_notifications "
            "(id, tenant_id, notification_type, title, message, severity, action_url, created_at) "
            "VALUES (:id,:tid,:nt,:ti,:me,:se,:au,NOW())"
        ), {"id": eid, "tid": tenant_id, "nt": notification_type,
            "ti": title, "me": message, "se": severity, "au": action_url})
        return eid

    def mark_notification_read(self, tenant_id, notification_id):
        self.db.execute(text(
            "UPDATE dbp_tenant_notifications SET is_read=true WHERE id=:id AND tenant_id=:tid"
        ), {"id": notification_id, "tid": tenant_id})
        return {"id": notification_id, "is_read": True}

    def list_notifications(self, tenant_id, is_read=None, severity=None, limit=50):
        q = "SELECT id, notification_type, title, message, severity, is_read, action_url, created_at FROM dbp_tenant_notifications WHERE tenant_id=:tid"
        params: dict[str, Any] = {"tid": tenant_id}
        if is_read is not None:
            q += " AND is_read=:ir"
            params["ir"] = is_read
        if severity:
            q += " AND severity=:se"
            params["se"] = severity
        q += " ORDER BY created_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(q), params).fetchall()
        return [{"id": r[0], "notification_type": r[1], "title": r[2],
                 "message": r[3], "severity": r[4], "is_read": r[5],
                 "action_url": r[6],
                 "created_at": str(r[7]) if r[7] else None} for r in rows]

    def get_notification(self, tenant_id, notification_id):
        r = self.db.execute(text(
            "SELECT id, notification_type, title, message, severity, is_read, action_url, created_at "
            "FROM dbp_tenant_notifications WHERE id=:id AND tenant_id=:tid"
        ), {"id": notification_id, "tid": tenant_id}).fetchone()
        if not r:
            return None
        return {"id": r[0], "notification_type": r[1], "title": r[2],
                "message": r[3], "severity": r[4], "is_read": r[5],
                "action_url": r[6], "created_at": str(r[7]) if r[7] else None}

    def delete_notification(self, tenant_id, notification_id):
        r = self.db.execute(text(
            "DELETE FROM dbp_tenant_notifications WHERE id=:id AND tenant_id=:tid"
        ), {"id": notification_id, "tid": tenant_id})
        return r.rowcount > 0
