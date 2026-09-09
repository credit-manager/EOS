"""Guard tenant isolation for tables created after the release migrations.

Revision ID: 20260909_finalize_tenant_rls_dynamic
Revises: 20260909_finalize_tenant_rls_payments
"""
from __future__ import annotations

from alembic import op

revision = "20260909_finalize_tenant_rls_dynamic"
down_revision = "20260909_finalize_tenant_rls_payments"
branch_labels = None
depends_on = None


_EVENT_FUNCTION = r"""
CREATE OR REPLACE FUNCTION public.eos_enforce_tenant_rls_on_ddl()
RETURNS event_trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    item record;
    policy_name text;
BEGIN
    IF pg_event_trigger_depth() > 1 THEN
        RETURN;
    END IF;

    FOR item IN
        SELECT c.relname
          FROM pg_event_trigger_ddl_commands() d
          JOIN pg_class c ON c.oid = d.objid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_attribute a ON a.attrelid = c.oid
                              AND a.attname = 'tenant_id'
                              AND NOT a.attisdropped
         WHERE n.nspname = 'public'
           AND c.relkind IN ('r', 'p')
           AND d.command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'ALTER TABLE')
    LOOP
        policy_name := left('tenant_isolation_' || item.relname, 63);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', item.relname);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', item.relname);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', policy_name, item.relname);
        EXECUTE format(
            'CREATE POLICY %I ON public.%I ' ||
            'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
            'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
            policy_name,
            item.relname
        );
    END LOOP;
END;
$$;
"""


def upgrade() -> None:
    op.execute(_EVENT_FUNCTION)
    op.execute("ALTER FUNCTION public.eos_enforce_tenant_rls_on_ddl() OWNER TO CURRENT_USER")
    op.execute("DROP EVENT TRIGGER IF EXISTS eos_tenant_rls_ddl_guard")
    op.execute(
        "CREATE EVENT TRIGGER eos_tenant_rls_ddl_guard "
        "ON ddl_command_end EXECUTE FUNCTION public.eos_enforce_tenant_rls_on_ddl()"
    )
    # Reconcile any tenant table that may have been created after the previous
    # release-RLS migration but before this dynamic guard was installed.
    op.execute(
        """
        DO $$
        DECLARE
            item record;
            policy_name text;
        BEGIN
            FOR item IN
                SELECT c.relname
                  FROM pg_class c
                  JOIN pg_namespace n ON n.oid=c.relnamespace
                  JOIN pg_attribute a ON a.attrelid=c.oid
                                      AND a.attname='tenant_id'
                                      AND NOT a.attisdropped
                 WHERE n.nspname='public'
                   AND c.relkind IN ('r','p')
                   AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)
            LOOP
                policy_name := left('tenant_isolation_' || item.relname, 63);
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', item.relname);
                EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', item.relname);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', policy_name, item.relname);
                EXECUTE format(
                    'CREATE POLICY %I ON public.%I ' ||
                    'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
                    'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                    policy_name, item.relname
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP EVENT TRIGGER IF EXISTS eos_tenant_rls_ddl_guard")
    op.execute("DROP FUNCTION IF EXISTS public.eos_enforce_tenant_rls_on_ddl()")
