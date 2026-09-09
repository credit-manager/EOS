"""Database-level accounting and inventory invariants against real PostgreSQL."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import psycopg2
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.infrastructure.db.foundation_models import InventoryMovementModel, StockBalanceModel
from eos_v2.infrastructure.db.foundation_repository import FoundationRepository
from eos_v2.modules.inventory import InventoryMovement


@pytest.mark.postgres

def test_postgres_accounting_integrity_and_tenant_ownership():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required for PostgreSQL integrity tests")

    tenant_a = uuid4()
    tenant_b = uuid4()
    account_a = uuid4()
    account_b = uuid4()
    entry_a = uuid4()

    with psycopg2.connect(url) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica")
            cur.execute(
                "INSERT INTO eos_v2_accounts(id, tenant_id, code, name, account_type) VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)",
                (account_a, tenant_a, "1000", "A Cash", "asset", account_b, tenant_b, "1000", "B Cash", "asset"),
            )
            cur.execute(
                "INSERT INTO eos_v2_journal_entries(id, tenant_id, entry_date, currency, description) VALUES (%s,%s,CURRENT_DATE,'USD','Integrity test')",
                (entry_a, tenant_a),
            )
            cur.execute("SET session_replication_role = DEFAULT")

            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO eos_v2_journal_lines(tenant_id,journal_entry_id,account_id,debit,credit) VALUES (%s,%s,%s,10,0)",
                    (tenant_a, entry_a, account_b),
                )
            conn.rollback()

            cur.execute(
                "INSERT INTO eos_v2_accounts(id, tenant_id, code, name, account_type) VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)",
                (account_a, tenant_a, "1000", "A Cash", "asset", account_b, tenant_b, "1000", "B Cash", "asset"),
            )
            cur.execute(
                "INSERT INTO eos_v2_journal_entries(id, tenant_id, entry_date, currency, description) VALUES (%s,%s,CURRENT_DATE,'USD','Integrity test')",
                (entry_a, tenant_a),
            )
            cur.execute(
                "INSERT INTO eos_v2_journal_lines(tenant_id,journal_entry_id,account_id,debit,credit) VALUES (%s,%s,%s,10,0)",
                (tenant_a, entry_a, account_a),
            )
            with pytest.raises(psycopg2.errors.RaiseException):
                conn.commit()
            conn.rollback()

            cur.execute(
                "INSERT INTO eos_v2_accounts(id, tenant_id, code, name, account_type) VALUES (%s,%s,%s,%s,%s),(%s,%s,%s,%s,%s)",
                (account_a, tenant_a, "1000", "A Cash", "asset", account_b, tenant_a, "4000", "A Revenue", "revenue"),
            )
            cur.execute(
                "INSERT INTO eos_v2_journal_entries(id, tenant_id, entry_date, currency, description, posted) VALUES (%s,%s,CURRENT_DATE,'USD','Posted test',TRUE)",
                (entry_a, tenant_a),
            )
            cur.execute(
                "INSERT INTO eos_v2_journal_lines(tenant_id,journal_entry_id,account_id,debit,credit) VALUES (%s,%s,%s,10,0),(%s,%s,%s,0,10)",
                (tenant_a, entry_a, account_a, tenant_a, entry_a, account_b),
            )
            conn.commit()

            with pytest.raises(psycopg2.errors.RaiseException):
                cur.execute("DELETE FROM eos_v2_journal_lines WHERE journal_entry_id=%s", (entry_a,))
            conn.rollback()


@pytest.mark.postgres

def test_postgres_inventory_updates_are_atomic_under_concurrency():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required for PostgreSQL integrity tests")

    engine = create_engine(url, pool_size=4, max_overflow=0, pool_pre_ping=True)
    tenant_id = uuid4()
    item_id = uuid4()
    token = set_tenant_context(TenantContext(tenant_id, uuid4()))
    try:
        with Session(engine) as session:
            session.add(StockBalanceModel(id=uuid4(), tenant_id=tenant_id, item_id=item_id, quantity=0))
            session.commit()

        barrier = Barrier(2)

        def apply_one() -> None:
            local_token = set_tenant_context(TenantContext(tenant_id, uuid4()))
            try:
                with Session(engine) as session:
                    movement = InventoryMovement(
                        tenant_id=tenant_id,
                        item_id=item_id,
                        warehouse_id=uuid4(),
                        quantity=1,
                        reference_type="concurrency-test",
                        reference_id=uuid4(),
                    )
                    barrier.wait(timeout=10)
                    FoundationRepository(session).apply_inventory_movement(movement)
                    session.commit()
            finally:
                reset_tenant_context(local_token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda _: apply_one(), range(2)))

        with Session(engine) as session:
            balance = session.scalar(
                select(StockBalanceModel).where(
                    StockBalanceModel.tenant_id == tenant_id,
                    StockBalanceModel.item_id == item_id,
                )
            )
            movements = session.scalars(
                select(InventoryMovementModel).where(
                    InventoryMovementModel.tenant_id == tenant_id,
                    InventoryMovementModel.item_id == item_id,
                )
            ).all()
            assert balance is not None
            assert balance.quantity == 2
            assert len(movements) == 2
    finally:
        reset_tenant_context(token)
        engine.dispose()
