"""
P15 Notification Engine — event→notification bridge.

Design:
  - EventBus events trigger notifications via templates
  - Templates use simple placeholders: {entity}, {record_id}, {user}, etc.
  - Users can set per-type/channel preferences (opt-out)
  - Notifications stored in dbp_notifications (persistent, tenant-scoped)
  - Channels: in_app (implemented), email (placeholder), future
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Default notification templates (built-in, created on first run)
DEFAULT_TEMPLATES = [
    {
        "code": "record.created",
        "event_type": "record.created",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "New {entity} record created",
        "message_template": "A new record was created in {entity} by {user}.",
    },
    {
        "code": "record.updated",
        "event_type": "record.updated",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "{entity} record updated",
        "message_template": "Record {record_id} in {entity} was updated by {user}.",
    },
    {
        "code": "record.deleted",
        "event_type": "record.deleted",
        "channel": "in_app",
        "notification_type": "warning",
        "title_template": "{entity} record deleted",
        "message_template": "Record {record_id} in {entity} was deleted by {user}.",
    },
    {
        "code": "record.restored",
        "event_type": "record.restored",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "{entity} record restored",
        "message_template": "Record {record_id} in {entity} was restored by {user}.",
    },
    {
        "code": "record.imported",
        "event_type": "record.imported",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "{entity} records imported",
        "message_template": "Records were imported into {entity} by {user}.",
    },
    {
        "code": "entity.created",
        "event_type": "entity.created",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "New entity '{entity}' created",
        "message_template": "Entity '{entity}' was created by {user}.",
    },
    {
        "code": "entity.deleted",
        "event_type": "entity.deleted",
        "channel": "in_app",
        "notification_type": "warning",
        "title_template": "Entity '{entity}' deleted",
        "message_template": "Entity '{entity}' was deleted by {user}.",
    },
    {
        "code": "record.bulk_created",
        "event_type": "record.bulk_created",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "Bulk records created in {entity}",
        "message_template": "Multiple records were created in {entity} by {user}.",
    },
    {
        "code": "record.bulk_updated",
        "event_type": "record.bulk_updated",
        "channel": "in_app",
        "notification_type": "info",
        "title_template": "Bulk records updated in {entity}",
        "message_template": "Multiple records were updated in {entity} by {user}.",
    },
    {
        "code": "record.bulk_deleted",
        "event_type": "record.bulk_deleted",
        "channel": "in_app",
        "notification_type": "warning",
        "title_template": "Bulk records deleted from {entity}",
        "message_template": "Multiple records were deleted from {entity} by {user}.",
    },
]


class NotificationEngine:
    """
    Bridges EventBus events to user notifications.
    Respects user preferences for opt-in/opt-out.
    """

    def __init__(self, db: Session):
        self.db = db

    def ensure_default_templates(self, tenant_id: str | None = None):
        """Create default templates if they don't exist (idempotent)."""
        for tmpl in DEFAULT_TEMPLATES:
            existing = self.db.execute(
                text("SELECT id FROM dbp_notification_templates WHERE code = :code"),
                {"code": tmpl["code"]},
            ).fetchone()
            if not existing:
                self.db.execute(
                    text(
                        "INSERT INTO dbp_notification_templates "
                        "(id, tenant_id, code, channel, notification_type, "
                        "title_template, message_template, event_type, is_active) "
                        "VALUES (:id, :tid, :code, :ch, :nt, :tt, :mt, :et, true)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tid": tenant_id,
                        "code": tmpl["code"],
                        "ch": tmpl["channel"],
                        "nt": tmpl["notification_type"],
                        "tt": tmpl["title_template"],
                        "mt": tmpl["message_template"],
                        "et": tmpl["event_type"],
                    },
                )
        self.db.flush()

    def process_event(
        self,
        event_type: str,
        entity_code: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        record_id: str | None = None,
        event_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Process an EventBus event → create notifications for affected users.
        Returns list of notification IDs created.
        """
        # Find matching templates
        templates = self.db.execute(
            text(
                "SELECT id, code, channel, notification_type, title_template, "
                "message_template "
                "FROM dbp_notification_templates "
                "WHERE event_type = :et AND is_active = true"
            ),
            {"et": event_type},
        ).fetchall()

        if not templates:
            return []

        created_ids = []

        # Determine target users:
        # - The user who performed the action gets notified (unless they're the only one)
        # - For now, send to all users in the tenant who have this notification type enabled
        target_users = self._get_target_users(tenant_id, event_type)

        for tmpl in templates:
            _tmpl_id, _code, channel, ntype, title_tmpl, msg_tmpl = tmpl

            # Build context for template
            ctx = {
                "entity": entity_code,
                "record_id": record_id or "",
                "user": user_id or "system",
                "event_type": event_type,
            }
            if payload:
                ctx.update({k: str(v) for k, v in payload.items()})

            title = _render_template(title_tmpl, ctx)
            message = _render_template(msg_tmpl, ctx) if msg_tmpl else None

            for target_user in target_users:
                # Check user preferences — is this notification enabled?
                if not self._is_enabled(target_user, ntype, channel):
                    continue

                notif_id = str(uuid.uuid4())
                self.db.execute(
                    text(
                        "INSERT INTO dbp_notifications "
                        "(id, tenant_id, user_id, channel, title, message, "
                        "notification_type, entity_code, record_id, event_id, "
                        "action_url, is_read, extra_data) "
                        "VALUES (:id, :tid, :uid, :ch, :title, :msg, :nt, "
                        ":ec, :rid, :eid, :au, false, :meta)"
                    ),
                    {
                        "id": notif_id,
                        "tid": tenant_id,
                        "uid": target_user,
                        "ch": channel,
                        "title": title,
                        "msg": message,
                        "nt": ntype,
                        "ec": entity_code,
                        "rid": record_id,
                        "eid": event_id,
                        "au": f"/entities/{entity_code}/records/{record_id}" if record_id else None,
                        "meta": "{}",
                    },
                )
                created_ids.append(notif_id)

        if created_ids:
            self.db.flush()

        return created_ids

    def _get_target_users(
        self, tenant_id: str | None, event_type: str
    ) -> list[str]:
        """
        Determine which users should receive notifications for this event.
        Returns list of user_id strings.
        Default: all users in the tenant who have active sessions.
        For now, returns all users with notification preferences in this tenant.
        """
        if not tenant_id:
            return []

        rows = self.db.execute(
            text(
                "SELECT DISTINCT user_id FROM dbp_notification_preferences "
                "WHERE tenant_id = :tid AND is_enabled = true"
            ),
            {"tid": tenant_id},
        ).fetchall()

        return [r[0] for r in rows]

    def _is_enabled(
        self, user_id: str, notification_type: str, channel: str
    ) -> bool:
        """Check if a user has enabled this notification type/channel."""
        pref = self.db.execute(
            text(
                "SELECT is_enabled FROM dbp_notification_preferences "
                "WHERE user_id = :uid AND notification_type = :nt AND channel = :ch"
            ),
            {"uid": user_id, "nt": notification_type, "ch": channel},
        ).fetchone()

        if pref is None:
            # No preference set → default enabled
            return True

        return bool(pref[0])

    # ──────────────────────────────────────────────────────────
    # DIRECT NOTIFICATION (bypass templates)
    # ──────────────────────────────────────────────────────────

    def create_notification(
        self,
        user_id: str,
        title: str,
        tenant_id: str | None = None,
        message: str | None = None,
        notification_type: str = "info",
        channel: str = "in_app",
        entity_code: str | None = None,
        record_id: str | None = None,
        event_id: str | None = None,
        action_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a direct notification (not from event).
        Used by workflow/approval/manual notifications.
        """
        notif_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO dbp_notifications "
                "(id, tenant_id, user_id, channel, title, message, "
                "notification_type, entity_code, record_id, event_id, "
                "action_url, is_read, extra_data) "
                "VALUES (:id, :tid, :uid, :ch, :title, :msg, :nt, "
                ":ec, :rid, :eid, :au, false, :meta)"
            ),
            {
                "id": notif_id,
                "tid": tenant_id,
                "uid": user_id,
                "ch": channel,
                "title": title,
                "msg": message,
                "nt": notification_type,
                "ec": entity_code,
                "rid": record_id,
                "eid": event_id,
                "au": action_url,
                "meta": "{}",
            },
        )
        self.db.flush()
        return notif_id

    # ──────────────────────────────────────────────────────────
    # MARK READ
    # ──────────────────────────────────────────────────────────

    def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            text(
                "UPDATE dbp_notifications SET is_read = true, read_at = :now "
                "WHERE id = :id AND user_id = :uid"
            ),
            {"id": notification_id, "uid": user_id, "now": now},
        )
        self.db.flush()
        self.db.commit()
        return result.rowcount > 0

    def mark_all_read(self, user_id: str, tenant_id: str | None = None) -> int:
        """Mark all notifications for a user as read. Returns count."""
        now = datetime.now(timezone.utc)
        query = "UPDATE dbp_notifications SET is_read = true, read_at = :now " \
                "WHERE user_id = :uid AND is_read = false"
        params: dict[str, Any] = {"uid": user_id, "now": now}

        if tenant_id:
            query += " AND tenant_id = :tid"
            params["tid"] = tenant_id

        result = self.db.execute(text(query), params)
        self.db.flush()
        self.db.commit()
        return result.rowcount


def _render_template(template: str, context: dict[str, Any]) -> str:
    """Simple {placeholder} rendering."""
    result = template
    for key, value in context.items():
        result = result.replace("{" + key + "}", str(value))
    return result
