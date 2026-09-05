"""Force tenant RLS for existing tenant-scoped tables.

The original hardening migration enabled RLS, but PostgreSQL table owners can
normally bypass it. This follow-up explicitly forces RLS so the application
role cannot accidentally bypass tenant policies.
"""
from alembic import op

revision = "20260905_force_tenant_rls"
down_revision = "20260905_financial_controls"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DO $$
    DECLARE
        r record;
    BEGIN
        FOR r IN
            SELECT DISTINCT c.table_schema, c.table_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE c.column_name = 'tenant_id'
              AND c.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
        LOOP
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', r.table_schema, r.table_name);
            EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY', r.table_schema, r.table_name);
        END LOOP;
    END $$;
    """)


def downgrade():
    op.execute("""
    DO $$
    DECLARE
        r record;
    BEGIN
        FOR r IN
            SELECT DISTINCT c.table_schema, c.table_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE c.column_name = 'tenant_id'
              AND c.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
        LOOP
            EXECUTE format('ALTER TABLE %I.%I NO FORCE ROW LEVEL SECURITY', r.table_schema, r.table_name);
        END LOOP;
    END $$;
    """)
