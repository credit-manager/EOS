"""Real PostgreSQL verification for audit isolation and outbox retry semantics."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import psycopg2
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.audit.service import record_event
from eos_v2.domain.workflow.events import DomainEvent
from eos_v2.infrastructure.events.outbox import SqlAlchemyOutbox

pytestmark = pytest.mark.postgres


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required for PostgreSQL audit/outbox tests")
    return url


def test_audit_rls_isolates_tenants_and_wrong_tenant_write_is_rejected() -> None:
    url = _database_url()
    tenant_a, tenant_b, event_id = uuid4(), uuid4(), uuid4()
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_a),))
            cur.execute("INSERT INTO eos_v2_audit_events (id, tenant_id, action, resource_type) VALUES (%s,%s,'test.created','test')", (event_id, tenant_a))
            conn.commit()
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_b),))
            cur.execute("SELECT count(*) FROM eos_v2_audit_events")
            assert cur.fetchone()[0] == 0
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute("INSERT INTO eos_v2_audit_events (id, tenant_id, action, resource_type) VALUES (%s,%s,'test.forbidden','test')", (uuid4(), tenant_a))
            conn.rollback()
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_a),))
            cur.execute("SELECT count(*) FROM eos_v2_audit_events WHERE id=%s", (event_id,))
            assert cur.fetchone()[0] == 1


def test_audit_failure_rolls_back_with_business_transaction() -> None:
    url = _database_url()
    tenant_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id, uuid4()))
    try:
        engine = create_engine(url, pool_pre_ping=True)
        try:
            with Session(engine) as session:
                record_event(session, action="transaction.test", resource_type="test", resource_id=uuid4())
                session.rollback()
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM eos_v2_audit_events WHERE tenant_id=%s AND action='transaction.test'", (tenant_id,))
                    assert cur.fetchone()[0] == 0
        finally:
            engine.dispose()
    finally:
        reset_tenant_context(token)


def test_outbox_rls_isolates_tenants_and_wrong_tenant_write_is_rejected() -> None:
    url = _database_url()
    tenant_a, tenant_b, event_id = uuid4(), uuid4(), uuid4()
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_a),))
            cur.execute(
                "INSERT INTO eos_v2_outbox_events (id, tenant_id, event_type, aggregate_id, payload, occurred_at) "
                "VALUES (%s,%s,'test.created',%s,'{}'::jsonb,CURRENT_TIMESTAMP)",
                (event_id, tenant_a, uuid4()),
            )
            conn.commit()
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_b),))
            cur.execute("SELECT count(*) FROM eos_v2_outbox_events")
            assert cur.fetchone()[0] == 0
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    "INSERT INTO eos_v2_outbox_events (id, tenant_id, event_type, aggregate_id, payload, occurred_at) "
                    "VALUES (%s,%s,'test.forbidden',%s,'{}'::jsonb,CURRENT_TIMESTAMP)",
                    (uuid4(), tenant_a, uuid4()),
                )
            conn.rollback()
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(tenant_a),))
            cur.execute("SELECT count(*) FROM eos_v2_outbox_events WHERE id=%s", (event_id,))
            assert cur.fetchone()[0] == 1


def test_outbox_retries_after_failed_publish_and_preserves_event_identity() -> None:
    url = _database_url()
    engine = create_engine(url, pool_pre_ping=True)
    tenant_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id, uuid4()))
    try:
        with Session(engine) as session:
            outbox = SqlAlchemyOutbox(session)
            event = DomainEvent(tenant_id, "test.retry", uuid4(), {"attempt": 1})
            outbox.append(event)
            session.commit()
            first = outbox.claim_unpublished(1)
            assert [item.id for item in first] == [event.id]
            first_token = first[0].claim_token
            assert first_token is not None
            session.commit()
            assert outbox.mark_published(event.id, uuid4()) is False
            session.rollback()
            session.execute(text("UPDATE eos_v2_outbox_events SET claimed_at = :expired WHERE id = :id"), {"expired": "2000-01-01T00:00:00+00:00", "id": event.id})
            session.commit()
            retry = outbox.claim_unpublished(1)
            assert [item.id for item in retry] == [event.id]
            retry_token = retry[0].claim_token
            assert retry_token is not None and retry_token != first_token
            assert retry[0].delivery_attempts >= 2
            assert outbox.mark_published(event.id, retry_token)
            session.commit()
            assert outbox.claim_unpublished(1) == []
    finally:
        reset_tenant_context(token)
        engine.dispose()


def test_outbox_postgres_workers_do_not_claim_same_rows() -> None:
    url = _database_url()
    engine = create_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True)
    tenant_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id, uuid4()))
    try:
        with Session(engine) as session:
            outbox = SqlAlchemyOutbox(session)
            for i in range(2):
                outbox.append(DomainEvent(tenant_id, "test.concurrent", uuid4(), {"n": i}))
            session.commit()
        barrier = Barrier(2)

        def claim_one() -> tuple[UUID, ...]:
            local_token = set_tenant_context(TenantContext(tenant_id, uuid4()))
            try:
                with Session(engine) as session:
                    barrier.wait(timeout=10)
                    ids = tuple(item.id for item in SqlAlchemyOutbox(session).claim_unpublished(1))
                    if ids:
                        session.commit()
                    return ids
            finally:
                reset_tenant_context(local_token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: claim_one(), range(2)))
        claimed_ids = [event_id for result in results for event_id in result]
        assert len(claimed_ids) == 2
        assert len(set(claimed_ids)) == 2
    finally:
        reset_tenant_context(token)
        engine.dispose()
