"""Defense-in-depth tenant isolation for tables carrying tenant_id.

The application still performs explicit tenant authorization. PostgreSQL RLS is
a second boundary and requires the application connection role to be configured
as a non-owner/non-BYPASSRLS role for enforcement to be effective.
"""
from alembic import op

revision = "20260902_tenant_rls_policies"
down_revision = "20260902_rate_limit_store"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DO $$
    DECLARE
        r record;
        policy_name text;
    BEGIN
        FOR r IN
            SELECT c.table_schema, c.table_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE c.column_name = 'tenant_id'
              AND c.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
        LOOP
            policy_name := 'tenant_isolation_' || r.table_name;
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', r.table_schema, r.table_name);
            EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', policy_name, r.table_schema, r.table_name);
            EXECUTE format(
                'CREATE POLICY %I ON %I.%I USING (tenant_id::text = current_setting(''app.tenant_id'', true) OR tenant_id IS NULL) WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                policy_name, r.table_schema, r.table_name
            );
        END LOOP;
    END $$;
    """)


def downgrade():
    op.execute("""
    DO $$
    DECLARE
        r record;
        policy_name text;
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
            policy_name := 'tenant_isolation_' || r.table_name;
            EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', policy_name, r.table_schema, r.table_name);
            EXECUTE format('ALTER TABLE %I.%I DISABLE ROW LEVEL SECURITY', r.table_schema, r.table_name);
        END LOOP;
    END $$;
    """)
