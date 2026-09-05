"""Live PostgreSQL smoke test for real tenant RLS enforcement."""
import os
import uuid
import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("EOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="EOS_TEST_DATABASE_URL not configured")


def test_live_tenant_rls_with_non_owner_role():
    engine = create_engine(DATABASE_URL, future=True)
    schema = "eos_e2e_" + uuid.uuid4().hex[:10]
    role = "eos_app_" + uuid.uuid4().hex[:10]
    table = f'"{schema}".bld_customer'
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE ROLE "{role}" LOGIN PASSWORD :pw'), {"pw": uuid.uuid4().hex})
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'''CREATE TABLE {table} (
                id UUID PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL, created_at TIMESTAMP NOT NULL
            )'''))
            conn.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY'))
            conn.execute(text(f'''CREATE POLICY tenant_isolation ON {table}
                USING (tenant_id = current_setting('app.tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.tenant_id', true))'''))
            conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
            conn.execute(text(f'GRANT SELECT ON {table} TO "{role}"'))
            conn.execute(text(f'''INSERT INTO {table} (id, tenant_id, name, created_at)
                VALUES (:id1,:a,'Tourism Customer',CURRENT_TIMESTAMP),
                       (:id2,:b,'Construction Customer',CURRENT_TIMESTAMP)'''),
                         {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()), "a": "tourism-a", "b": "construction-b"})

        app_engine = create_engine(DATABASE_URL, future=True)
        with app_engine.connect() as conn:
            conn.execute(text(f'SET ROLE "{role}"'))
            conn.execute(text("SELECT set_config('app.tenant_id', 'tourism-a', true)"))
            rows = conn.execute(text(f'SELECT name FROM {table} ORDER BY name')).scalars().all()
            assert rows == ["Tourism Customer"]
            conn.execute(text("RESET ROLE"))
            conn.rollback()
        app_engine.dispose()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        engine.dispose()
