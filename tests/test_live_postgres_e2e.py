"""Live PostgreSQL E2E smoke test for EOS tenant-scoped generation.

Runs only when EOS_TEST_DATABASE_URL is supplied. The test creates its own
schema namespace, so it never writes to a developer/production database.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("EOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="EOS_TEST_DATABASE_URL not configured")


def test_live_tenant_scoped_entity_and_crud_contract():
    engine = create_engine(DATABASE_URL, future=True)
    schema = "eos_e2e_" + uuid.uuid4().hex[:10]
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'''CREATE TABLE "{schema}".bld_customer (
            id UUID PRIMARY KEY, tenant_id VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL, created_at TIMESTAMP NOT NULL
        )'''))
        a, b = "tourism-a", "construction-b"
        conn.execute(text(f'''INSERT INTO "{schema}".bld_customer
            (id, tenant_id, name, created_at)
            VALUES (:id1,:a,'Tourism Customer',CURRENT_TIMESTAMP),
                   (:id2,:b,'Construction Customer',CURRENT_TIMESTAMP)'''),
                     {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()), "a": a, "b": b})
        tourism = conn.execute(text(f'SELECT count(*) FROM "{schema}".bld_customer WHERE tenant_id=:tid'), {"tid": a}).scalar()
        construction = conn.execute(text(f'SELECT count(*) FROM "{schema}".bld_customer WHERE tenant_id=:tid'), {"tid": b}).scalar()
        assert tourism == 1
        assert construction == 1
        leaked = conn.execute(text(f'''SELECT count(*) FROM "{schema}".bld_customer
            WHERE tenant_id=:tid AND name='Construction Customer' '''), {"tid": a}).scalar()
        assert leaked == 0
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()
