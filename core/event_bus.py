"""
P12 Event Bus — synchronous event emission and webhook delivery.

Design:
  - Events are stored in dbp_events (persistent log)
  - Active webhooks are matched and deliveries created
  - Delivery is synchronous (caller blocks, same transaction)
  - Retry handled via next_retry_at for async workers later
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class EventBus:
    """
    Synchronous event emitter.
    Events are stored in the DB within the caller's transaction.
    Webhook delivery is triggered but NOT blocking the transaction.
    """

    VALID_EVENT_TYPES = {
        "record.created", "record.updated", "record.deleted", "record.restored",
        "record.bulk_created", "record.bulk_updated", "record.bulk_deleted",
        "record.imported",
        "entity.created", "entity.updated", "entity.deleted",
        "field.added", "field.updated", "field.removed",
        "relationship.created", "relationship.deleted",
    }

    MAX_WEBHOOK_RETRIES = 3

    def __init__(self, db: Session):
        self.db = db

    def emit(
        self,
        event_type: str,
        entity_code: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        record_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Emit an event. Stores in DB and triggers webhook deliveries.
        Returns event_id or None on failure.
        Never raises — events are best-effort.
        """
        if event_type not in self.VALID_EVENT_TYPES:
            return None

        try:
            event_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.db.execute(
                text(
                    "INSERT INTO dbp_events (id, tenant_id, event_type, entity_code, "
                    "record_id, user_id, payload, created_at) "
                    "VALUES (:id, :tid, :et, :ec, :rid, :uid, :payload, :ts)"
                ),
                {
                    "id": event_id,
                    "tid": tenant_id,
                    "et": event_type,
                    "ec": entity_code,
                    "rid": record_id,
                    "uid": user_id,
                    "payload": json.dumps(payload) if payload else None,
                    "ts": now,
                },
            )
            self.db.flush()

            self._trigger_webhooks_raw(event_id, entity_code, event_type)
            self._trigger_notifications(event_id, entity_code, event_type,
                                       tenant_id, user_id, record_id, payload)

            return event_id

        except Exception:
            return None

    def _trigger_webhooks_raw(self, event_id: str, entity_code: str, event_type: str) -> None:
        """Find matching webhooks and create delivery records using raw SQL."""
        try:
            rows = self.db.execute(
                text(
                    "SELECT id, target_url, secret, event_types, custom_headers "
                    "FROM dbp_webhooks "
                    "WHERE entity_code = :ec AND is_active = true"
                ),
                {"ec": entity_code},
            ).fetchall()

            for row in rows:
                webhook_id, url, secret, event_types, headers = row[0], row[1], row[2], row[3] or [], row[4] or {}

                if event_type not in event_types and "*" not in event_types:
                    continue

                delivery_id = str(uuid.uuid4())
                self.db.execute(
                    text(
                        "INSERT INTO dbp_webhook_deliveries "
                        "(id, webhook_id, event_id, status, attempts) "
                        "VALUES (:id, :wid, :eid, 'pending', 0)"
                    ),
                    {"id": delivery_id, "wid": webhook_id, "eid": event_id},
                )

            self.db.flush()

        except Exception:
            pass

    def _trigger_notifications(
        self, event_id: str, entity_code: str, event_type: str,
        tenant_id: str | None, user_id: str | None,
        record_id: str | None, payload: dict[str, Any] | None,
    ) -> None:
        """Process event → create notifications via NotificationEngine."""
        try:
            from core.notification_engine import NotificationEngine
            engine = NotificationEngine(self.db)
            engine.process_event(
                event_type=event_type,
                entity_code=entity_code,
                tenant_id=tenant_id,
                user_id=user_id,
                record_id=record_id,
                event_id=event_id,
                payload=payload,
            )
            self.db.flush()
        except Exception:
            pass

    def get_events(
        self,
        entity_code: str | None = None,
        event_type: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query events with optional filters."""
        conditions = []
        params = {"limit": limit, "offset": offset}

        if entity_code:
            conditions.append("entity_code = :ec")
            params["ec"] = entity_code
        if event_type:
            conditions.append("event_type = :et")
            params["et"] = event_type
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id

        where = " AND ".join(conditions) if conditions else "1=1"

        rows = self.db.execute(
            text(
                f"SELECT id, tenant_id, event_type, entity_code, record_id, "
                f"user_id, payload, created_at "
                f"FROM dbp_events WHERE {where} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()

        return [
            {
                "id": r[0],
                "tenant_id": r[1],
                "event_type": r[2],
                "entity_code": r[3],
                "record_id": r[4],
                "user_id": r[5],
                "payload": r[6] if isinstance(r[6], dict) else json.loads(r[6]) if r[6] else None,
                "created_at": str(r[7]) if r[7] else None,
            }
            for r in rows
        ]

    def get_event(self, event_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        """Get a single event by ID with optional tenant isolation."""
        conditions = ["id = :eid"]
        params: dict[str, Any] = {"eid": event_id}

        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id

        where = " AND ".join(conditions)

        row = self.db.execute(
            text(
                f"SELECT id, tenant_id, event_type, entity_code, record_id, "
                f"user_id, payload, created_at "
                f"FROM dbp_events WHERE {where}"
            ),
            params,
        ).fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "tenant_id": row[1],
            "event_type": row[2],
            "entity_code": row[3],
            "record_id": row[4],
            "user_id": row[5],
            "payload": row[6] if isinstance(row[6], dict) else json.loads(row[6]) if row[6] else None,
            "created_at": str(row[7]) if row[7] else None,
        }


def sign_payload(payload: str, secret: str) -> str:
    """HMAC-SHA256 signature for webhook verification."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
