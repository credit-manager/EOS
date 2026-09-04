"""Tenant-safe reliability primitives for critical write paths."""
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
        self.db.execute(text("""
            INSERT INTO dbp_idempotency_keys (id, tenant_id, key, request_hash, created_at)
            VALUES (:id, :tenant_id, :key, :request_hash, :created_at)
            ON CONFLICT (tenant_id, key) DO NOTHING
        """), {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "key": key,
               "request_hash": request_hash, "created_at": datetime.now(timezone.utc)})
        row = self.db.execute(text("""
            SELECT request_hash, status_code, response_body, completed_at
            FROM dbp_idempotency_keys
            WHERE tenant_id=:tenant_id AND key=:key
            FOR UPDATE
        """), {"tenant_id": tenant_id, "key": key}).fetchone()
        if not row:
            raise RuntimeError("Unable to reserve idempotency key")
        if row.request_hash != request_hash:
            raise IdempotencyConflict("Idempotency key was already used with a different request")
        if row.completed_at is None and row.status_code is not None:
            raise IdempotencyInProgress("A request with this idempotency key is already in progress")
        if row.completed_at is None:
            return None
        return {"status_code": row.status_code, "response_body": json.loads(row.response_body or "null")}

    def complete(self, tenant_id: str, key: str, status_code: int, response_body: Any) -> None:
        result = self.db.execute(text("""
            UPDATE dbp_idempotency_keys
            SET status_code=:status_code, response_body=:response_body, completed_at=:completed_at
            WHERE tenant_id=:tenant_id AND key=:key AND completed_at IS NULL
        """), {"tenant_id": tenant_id, "key": key, "status_code": status_code,
               "response_body": json.dumps(response_body, default=str),
               "completed_at": datetime.now(timezone.utc)})
        if getattr(result, "rowcount", 1) == 0:
            raise RuntimeError("Idempotency key is missing or already completed")


class OutboxStore:
    """Transactional outbox access; the caller owns the surrounding transaction."""
    def __init__(self, db):
        self.db = db

    def enqueue(self, tenant_id: str, event_type: str, aggregate_type: str, aggregate_id: str, payload: dict) -> str:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        event_id = str(uuid.uuid4())
        row = self.db.execute(text("""
            INSERT INTO dbp_outbox_events
                (id, tenant_id, event_type, aggregate_type, aggregate_id, payload)
            VALUES (:id, :tenant_id, :event_type, :aggregate_type, :aggregate_id, :payload)
            ON CONFLICT (tenant_id, event_type, aggregate_type, aggregate_id) DO UPDATE
                SET aggregate_id = EXCLUDED.aggregate_id
            RETURNING id
        """), {"id": event_id, "tenant_id": tenant_id, "event_type": event_type,
               "aggregate_type": aggregate_type, "aggregate_id": aggregate_id,
               "payload": json.dumps(payload, default=str)}).fetchone()
        if not row:
            raise RuntimeError("Unable to enqueue outbox event")
        return str(row[0])

    def claim_batch(self, tenant_id: str, limit: int = 50) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        rows = self.db.execute(text("""
            SELECT id, event_type, aggregate_type, aggregate_id, payload, attempts
            FROM dbp_outbox_events
            WHERE tenant_id=:tenant_id AND status='pending' AND available_at<=NOW()
            ORDER BY created_at
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        """), {"tenant_id": tenant_id, "limit": limit}).fetchall()
        return [dict(r._mapping) for r in rows]

    def mark_processing(self, event_id: str, tenant_id: str) -> None:
        self.db.execute(text("UPDATE dbp_outbox_events SET status='processing', attempts=attempts+1 WHERE id=:id AND tenant_id=:tenant_id AND status='pending'"), {"id": event_id, "tenant_id": tenant_id})

    def mark_processed(self, event_id: str, tenant_id: str) -> None:
        self.db.execute(text("UPDATE dbp_outbox_events SET status='processed', processed_at=NOW(), last_error=NULL WHERE id=:id AND tenant_id=:tenant_id"), {"id": event_id, "tenant_id": tenant_id})

    def mark_failed(self, event_id: str, tenant_id: str, error: str) -> None:
        self.db.execute(text("UPDATE dbp_outbox_events SET status='pending', last_error=:error, available_at=NOW() + LEAST(3600, POWER(2, attempts)) * INTERVAL '1 second' WHERE id=:id AND tenant_id=:tenant_id"), {"id": event_id, "tenant_id": tenant_id, "error": error[:4000]})
