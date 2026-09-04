"""Reference outbox dispatcher with tenant context and bounded retries.

The dispatcher is transport-agnostic so deployments can invoke it from Celery,
RQ, a Kubernetes Job, or a dedicated worker without changing business code.
"""
from __future__ import annotations

import logging

from core.reliability import OutboxStore

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(self, db, handler):
        self.db = db
        self.handler = handler

    def dispatch_tenant(self, tenant_id: str, limit: int = 50) -> int:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        store = OutboxStore(self.db)
        events = store.claim_batch(tenant_id, limit)
        if not events:
            return 0
        # claim_batch atomically transitions all selected rows to processing.
        # Commit that state before invoking external handlers so a slow handler
        # never holds database row locks.
        self.db.commit()
        processed = 0
        for event in events:
            event_id = event["id"]
            try:
                self.handler(
                    tenant_id=tenant_id,
                    event_type=event["event_type"],
                    aggregate_type=event["aggregate_type"],
                    aggregate_id=event["aggregate_id"],
                    payload=event["payload"],
                )
                store.mark_processed(event_id, tenant_id)
                self.db.commit()
                processed += 1
            except Exception as exc:
                self.db.rollback()
                try:
                    store.mark_failed(event_id, tenant_id, str(exc))
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                logger.exception("Outbox event failed", extra={"tenant_id": tenant_id, "event_id": event_id})
        return processed
