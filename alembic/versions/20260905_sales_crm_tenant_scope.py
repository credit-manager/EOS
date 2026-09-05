"""Add tenant ownership to legacy direct Sales CRM tables.

The direct React CRM surface uses the legacy customers/leads/opportunities tables.
Those tables previously had no tenant discriminator, making authenticated access
insufficient to guarantee tenant isolation. Existing rows with NULL tenant_id are
intentionally hidden from tenant-scoped APIs until explicitly migrated/assigned.
"""
from alembic import op

revision = "20260905_sales_crm_tenant_scope"
down_revision = "20260905_force_tenant_rls"
branch_labels = None
depends_on = None

_TABLES = ("customers", "leads", "opportunities")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table!r}') IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1 FROM information_schema.columns
                       WHERE table_schema = 'public'
                         AND table_name = '{table}'
                         AND column_name = 'tenant_id'
                   ) THEN
                    ALTER TABLE public."{table}" ADD COLUMN tenant_id VARCHAR(36);
                END IF;
            END $$;
            """
        )
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table!r}') IS NOT NULL THEN
                    CREATE INDEX IF NOT EXISTS "idx_{table}_tenant_id" ON public."{table}" (tenant_id);
                    ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE public."{table}" FORCE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS "tenant_isolation_{table}" ON public."{table}";
                    CREATE POLICY "tenant_isolation_{table}" ON public."{table}"
                        USING (tenant_id::text = current_setting('app.tenant_id', true))
                        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table!r}') IS NOT NULL THEN
                    DROP POLICY IF EXISTS "tenant_isolation_{table}" ON public."{table}";
                    ALTER TABLE public."{table}" NO FORCE ROW LEVEL SECURITY;
                    ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;
                    DROP INDEX IF EXISTS "idx_{table}_tenant_id";
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = '{table}'
                          AND column_name = 'tenant_id'
                    ) THEN
                        ALTER TABLE public."{table}" DROP COLUMN tenant_id;
                    END IF;
                END IF;
            END $$;
            """
        )
