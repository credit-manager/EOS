"""Database-level accounting invariants against real PostgreSQL."""
from __future__ import annotations

import os
from uuid import uuid4

import psycopg2
import pytest


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

            # The composite FK must reject an account belonging to another tenant.
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
            # The deferred balance trigger must reject an incomplete/unbalanced entry at commit.
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
