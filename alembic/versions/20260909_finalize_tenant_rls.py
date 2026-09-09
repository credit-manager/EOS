"""Finalize tenant RLS after the complete canonical schema exists.

Revision ID: 20260909_finalize_tenant_rls
Revises: 20260909_merge_release_heads

The release head runs after schema restoration and normalizes tenant isolation
for every public table that actually has a tenant_id column, including
partitioned tables. The catalog scan prevents tenant tables from silently
escaping the RLS contract because of naming conventions or physical layout.
"""

from alembic import op

revision = "20260909_finalize_tenant_rls"
down_revision = "20260909_merge_release_heads"
branch_labels = None
depends_on = None


RLS_POLICY_PREFIX = "tenant_isolation_"


def _migration_block(down: bool = False) -> str:
    if down:
        return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN pg_attribute AS a ON a.attrelid = c.oid
                                           AND a.attname = 'tenant_id'
                                           AND NOT a.attisdropped
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p')
            LOOP
                v_policy_name := '{RLS_POLICY_PREFIX}' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', v_table_name);
            END LOOP;
        END $$;
        """

    return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT DISTINCT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN pg_attribute AS a ON a.attrelid = c.oid
                                           AND a.attname = 'tenant_id'
                                           AND NOT a.attisdropped
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p')
            LOOP
                v_policy_name := '{RLS_POLICY_PREFIX}' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format(
                    'CREATE POLICY %I ON public.%I ' ||
                    'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
                    'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                    v_policy_name, v_table_name
                );
            END LOOP;
        END $$;
        """


def upgrade() -> None:
    op.execute(_migration_block())


def downgrade() -> None:
    op.execute(_migration_block(down=True))
