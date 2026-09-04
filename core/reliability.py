"""Tenant-safe reliability primitives used by critical write paths.

The primitives deliberately use the caller's database transaction. A caller can
reserve an idempotency key, perform its business mutation, enqueue an outbox
event, and commit once. A rollback therefore rolls back all three operations.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


class IdempotencyConflict(ValueError):
    """The same key was reused with a different request payload."""


class IdempotencyInProgress(RuntimeError):
    """Another request currently owns the idempotency key."""


class IdempotencyStore:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def request_hash(payload: Any) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def reserve(self, tenant_id: str, key: str, payload: Any) -> dict | None:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        key = key.strip()
        if not key or len(key) > 255:
            raise ValueError("idempotency key must contain 1-255 characters")
        request_hash = self.request_hash(payload)
        row = self.db.execute(
            text("""
                SELECT id, request_hash, status_code, response_body, completed_at
                FROM dbp_idempotency_keys
                WHERE tenant_id = :tenant_id AND key = :key
                FOR UPDATE
            """),
            {"tenant_id": tenant_id, "key": key},
        ).fetchone()
        if row:
            if row.request_hash != request_hash:
                raise IdempotencyConflict("Idempotency key was already used with a different request")
            if row.completed_at is None:
                raise IdempotencyInProgress("A request with this idempotency key is already in progress")
            return {"status_code": row.status_code, "response_body": json.loads(row.response_body or "null")}

        self.db.execute(
            text("""
                INSERT INTO dbp_idempotency_keys
                    (id, tenant_id, key, request_hash, created_at)
                VALUES (:id, :tenant_id, :key, :request_hash, :created_at)
            """),
            {
                "id": str(uuid.uuid4()), "tenant_id": tenant_id, "key": key,
                "request_hash": request_hash, "created_at": datetime.now(timezone.utc),
            },
        )
        return None

    def complete(self, tenant_id: str, key: str, status_code: int, response_body: Any) -> None:
        self.db.execute(
            text("""
                UPDATE dbp_idempotency_keys
                SET status_code = :status_code,
                    response_body = :response_body,
                    completed_at = :completed_at
                WHERE tenant_id = :tenant_id AND key = :key
            """),
            {
                "tenant_id": tenant_id, "key": key, "status_code": status_code,
                "response_body": json.dumps(response_body, default=str),
                "completed_at": datetime.now(timezone.utc),
            },
        )


class OutboxStore:
    def __init__(self, db):
        self.db = db

    def enqueue(
        self,
        tenant_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> str:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        event_id = str(uuid.uuid4())
        self.db.execute(
            text("""
                INSERT INTO dbp_outbox_events
                    (id, tenant_id, event_type, aggregate_type, aggregate_id, payload)
                VALUES (:id, :tenant_id, :event_type, :aggregate_type, :aggregate_id, :payload)
                ON CONFLICT (tenant_id, event_type, aggregate_type, aggregate_id) DO NOTHING
            """),
            {
                "id": event_id, "tenant_id": tenant_id, "event_type": event_type,
                "aggregate_type": aggregate_type, "aggregate_id": aggregate_id,
                "payload": json.dumps(payload, default=str),
            },
        )
        return event_id

    def claim_batch(self, tenant_id: str, limit: int = 50) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        rows = self.db.execute(
            text("""
                SELECT id, event_type, aggregate_type, aggregate_id, payload, attempts
                FROM dbp_outbox_events
                WHERE tenant_id = :tenant_id
                  AND status = 'pending'
                  AND available_at <= NOW()
                ORDER BY created_at
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            """),
            {"tenant_id": tenant_id, "limit": limit},
        ).fetchall()
        ids = [r.id for r in rows]
        if ids:
            self.db.execute(
                text("UPDATE dbp_outbox_events SET status='processing', attempts=attempts+1 WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
        return [dict(r._mapping) for r in rows]

    def mark_processed(self, event_id: str, tenant_id: str) -> None:
        self.db.execute(
            text("""
                UPDATE dbp_outbox_events
                SET status='processed', processed_at=NOW(), last_error=NULL
                WHERE id=:id AND tenant_id=:tenant_id
            """), {"id": event_id, "tenant_id": tenant_id},
        )

    def mark_failed(self, event_id: str, tenant_id: str, error: str) -> None:
        self.db.execute(
            text("""
                UPDATE dbp_outbox_events
                SET status='pending', last_error=:error,
                    available_at=NOW() + LEAST(3600, POWER(2, attempts)) * INTERVAL '1 second'
                WHERE id=:id AND tenant_id=:tenant_id
            """), {"id": event_id, "tenant_id": tenant_id, "error": error[:4000]},
        )
