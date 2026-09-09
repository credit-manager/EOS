"""Live PostgreSQL E2E test for real tenant RLS enforcement.

The test is intentionally skipped unless EOS_TEST_DATABASE_URL is configured.
When enabled, it uses a non-owner application role and verifies SELECT, INSERT,
UPDATE and DELETE cannot cross the authenticated tenant boundary.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("EOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="EOS_TEST_DATABASE_URL not configured")


def test_live_tenant_rls_crud_isolation_with_non_owner_role():
    engine = create_engine(DATABASE_URL, future=True)
    schema = "eos_e2e_" + uuid.uuid4().hex[:10]
    role = "eos_app_" + uuid.uuid4().hex[:10]
    role_password = uuid.uuid4().hex
    table = f'"{schema}".bld_customer'
    customer_a = str(uuid.uuid4())
    customer_b = str(uuid.uuid4())
    customer_c = str(uuid.uuid4())

    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE ROLE "{role}" LOGIN PASSWORD :pw'), {"pw": role_password})
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'''CREATE TABLE {table} (
                id UUID PRIMARY KEY,
                tenant_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL
            )'''))
            conn.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY'))
            conn.execute(text(f'''CREATE POLICY tenant_isolation ON {table}
                USING (tenant_id = current_setting('app.tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.tenant_id', true))'''))
            conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
            conn.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO "{role}"'))
            conn.execute(text(f'''INSERT INTO {table} (id, tenant_id, name, created_at)
                VALUES (:id_a, :tenant_a, 'Tourism Customer', CURRENT_TIMESTAMP),
                       (:id_b, :tenant_b, 'Construction Customer', CURRENT_TIMESTAMP)'''),
                         {"id_a": customer_a, "id_b": customer_b,
                          "tenant_a": "tourism-a", "tenant_b": "construction-b"})

        app_engine = create_engine(DATABASE_URL, future=True)
        with app_engine.connect() as conn:
            conn.execute(text(f'SET ROLE "{role}"'))
            conn.execute(text("SELECT set_config('app.tenant_id', 'tourism-a', false)"))

            # SELECT: tenant A sees only tenant A.
            rows = conn.execute(text(f'SELECT id, name FROM {table} ORDER BY name')).all()
            assert rows == [(uuid.UUID(customer_a), "Tourism Customer")]

            # UPDATE: tenant A cannot modify tenant B.
            result = conn.execute(
                text(f'UPDATE {table} SET name = :name WHERE id = :id'),
                {"name": "Should Not Change", "id": customer_b},
            )
            assert result.rowcount == 0

            # DELETE: tenant A cannot delete tenant B.
            result = conn.execute(
                text(f'DELETE FROM {table} WHERE id = :id'),
                {"id": customer_b},
            )
            assert result.rowcount == 0

            # INSERT: tenant A cannot create a row owned by tenant B.
            with pytest.raises(Exception):
                conn.execute(
                    text(f'''INSERT INTO {table} (id, tenant_id, name, created_at)
                        VALUES (:id, :tenant, :name, CURRENT_TIMESTAMP)'''),
                    {"id": customer_c, "tenant": "construction-b", "name": "Cross Tenant Insert"},
                )
            conn.rollback()

        # Verify the database owner can clean up the test objects.
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
    finally:
        try:
            with engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        finally:
            app_engine.dispose() if 'app_engine' in locals() else None
            engine.dispose()
