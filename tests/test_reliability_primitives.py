"""Unit tests for tenant-scoped idempotency and transactional outbox primitives."""
import json

import pytest

from core.reliability import IdempotencyConflict, IdempotencyStore, OutboxStore


class FakeResult:
    def __init__(self, row=None, rowcount=1):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return [] if self._row is None else [self._row]


class FakeDB:
    """Small SQL recorder for deterministic unit tests without PostgreSQL."""
    def __init__(self):
        self.calls = []
        self.row = None
        self.outbox_id = None

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        sql = str(statement)
        if sql.lstrip().startswith("SELECT request_hash"):
            return FakeResult(self.row)
        if "INSERT INTO dbp_outbox_events" in sql and "RETURNING id" in sql:
            self.outbox_id = (params or {}).get("id")
            return FakeResult((self.outbox_id,))
        if "UPDATE dbp_idempotency_keys" in sql:
            return FakeResult(rowcount=1)
        return FakeResult()


def test_idempotency_hash_is_stable():
    payload_a = {"amount": "10", "currency": "SAR"}
    payload_b = {"currency": "SAR", "amount": "10"}
    assert IdempotencyStore.request_hash(payload_a) == IdempotencyStore.request_hash(payload_b)


def test_idempotency_reserve_creates_scoped_record():
    db = FakeDB()
    assert IdempotencyStore(db).reserve("tenant-a", "pay-1", {"amount": "10"}) is None
    insert = next(params for sql, params in db.calls if "INSERT INTO dbp_idempotency_keys" in sql)
    assert insert["tenant_id"] == "tenant-a"
    assert insert["key"] == "pay-1"


def test_idempotency_rejects_payload_reuse():
    db = FakeDB()
    original = {"amount": "10"}
    db.row = type("Row", (), {
        "request_hash": IdempotencyStore.request_hash(original),
        "status_code": 200,
        "response_body": json.dumps({"transaction_id": "t1"}),
        "completed_at": "done",
    })()
    with pytest.raises(IdempotencyConflict):
        IdempotencyStore(db).reserve("tenant-a", "pay-1", {"amount": "11"})


def test_idempotency_completion_is_tenant_scoped():
    db = FakeDB()
    IdempotencyStore(db).complete("tenant-a", "pay-1", 201, {"ok": True})
    sql, params = db.calls[-1]
    assert "completed_at IS NULL" in sql
    assert params["tenant_id"] == "tenant-a"


def test_outbox_enqueue_is_tenant_scoped_and_deduplicated():
    db = FakeDB()
    event_id = OutboxStore(db).enqueue("tenant-a", "payment.created", "payment", "p1", {"amount": 10})
    assert event_id == db.outbox_id
    sql, params = next((sql, params) for sql, params in db.calls if "INSERT INTO dbp_outbox_events" in sql)
    assert "ON CONFLICT" in sql
    assert params["tenant_id"] == "tenant-a"
    assert params["aggregate_id"] == "p1"


def test_outbox_claim_is_atomic_and_tenant_scoped():
    db = FakeDB()
    OutboxStore(db).claim_batch("tenant-a", 25)
    sql, params = db.calls[-1]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "SET status='processing'" in sql
    assert params["tenant_id"] == "tenant-a"
    assert params["limit"] == 25


def test_outbox_requires_tenant():
    with pytest.raises(ValueError):
        OutboxStore(FakeDB()).enqueue("", "x", "y", "z", {})
    with pytest.raises(ValueError):
        OutboxStore(FakeDB()).claim_batch("", 10)
