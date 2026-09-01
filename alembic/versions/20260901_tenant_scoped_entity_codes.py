"""Allow the same custom entity code in different tenants.

Global/system entities (tenant_id IS NULL) remain globally unique.
Tenant entities are unique only within their tenant.
"""
from alembic import op

revision = "20260901_tenant_entity_codes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DO $$
    DECLARE r record;
    BEGIN
      FOR r IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
        WHERE t.relname = 'dbp_entities'
          AND c.contype = 'u'
          AND a.attname = 'code'
      LOOP
        EXECUTE format('ALTER TABLE public.dbp_entities DROP CONSTRAINT IF EXISTS %I', r.conname);
      END LOOP;
    END $$;
    """)
    op.execute("""
    DO $$
    DECLARE r record;
    BEGIN
      FOR r IN
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname='public' AND tablename='dbp_entities'
          AND indexdef ILIKE '%UNIQUE%'
          AND indexdef ILIKE '%(code)%'
      LOOP
        EXECUTE format('DROP INDEX IF EXISTS public.%I', r.indexname);
      END LOOP;
    END $$;
    """)
    op.execute("""
      CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_entities_tenant_code
      ON public.dbp_entities (tenant_id, code)
      WHERE tenant_id IS NOT NULL
    """)
    op.execute("""
      CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_entities_global_code
      ON public.dbp_entities (code)
      WHERE tenant_id IS NULL
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS public.uq_dbp_entities_tenant_code")
    op.execute("DROP INDEX IF EXISTS public.uq_dbp_entities_global_code")
    op.execute("""
      CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_entities_code_legacy
      ON public.dbp_entities (code)
    """)
