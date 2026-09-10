"""Create tenant-isolated SaaS payment tables.

Revision ID: 20260909_finalize_tenant_rls_payments
Revises: 20260909_finalize_tenant_rls_accounting
"""
from __future__ import annotations

from alembic import op

revision = "20260909_finalize_tenant_rls_payments"
down_revision = "20260909_finalize_tenant_rls_accounting"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
    op.execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table}" ON public.{table}')
    op.execute(
        f'''CREATE POLICY "tenant_isolation_{table}" ON public.{table}
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))'''
    )


def _add_constraint_if_missing(table: str, constraint_name: str, expression: str) -> None:
    op.execute(
        f"""DO $$
        BEGIN
            ALTER TABLE public.{table}
              ADD CONSTRAINT {constraint_name} CHECK ({expression});
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;"""
    )


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS public.dbp_payment_gateways (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            gateway_name text NOT NULL,
            gateway_type text NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            config jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS public.dbp_payment_transactions (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            gateway_id text NULL,
            transaction_type text NOT NULL,
            amount numeric(20,4) NOT NULL,
            currency varchar(3) NOT NULL DEFAULT 'SAR',
            status text NOT NULL DEFAULT 'pending',
            reference_type text NULL,
            reference_id text NULL,
            customer_id text NULL,
            payment_method text NULL,
            gateway_response jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz NULL
        )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS public.dbp_payment_links (
            id text PRIMARY KEY,
            tenant_id text NOT NULL,
            link_token text NOT NULL UNIQUE,
            amount numeric(20,4) NOT NULL,
            currency varchar(3) NOT NULL DEFAULT 'SAR',
            description text NULL,
            customer_email text NULL,
            status text NOT NULL DEFAULT 'active',
            expires_at timestamptz NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )"""
    )

    _add_constraint_if_missing("dbp_payment_transactions", "ck_payment_transactions_amount_positive", "amount > 0")
    _add_constraint_if_missing("dbp_payment_transactions", "ck_payment_transactions_currency", "currency ~ '^[A-Z]{3}$'")
    _add_constraint_if_missing("dbp_payment_transactions", "ck_payment_transactions_type", "transaction_type IN ('payment','refund','authorization','capture')")
    _add_constraint_if_missing("dbp_payment_transactions", "ck_payment_transactions_status", "status IN ('pending','completed','failed','cancelled')")
    _add_constraint_if_missing("dbp_payment_links", "ck_payment_links_amount_positive", "amount > 0")
    _add_constraint_if_missing("dbp_payment_links", "ck_payment_links_currency", "currency ~ '^[A-Z]{3}$'")
    _add_constraint_if_missing("dbp_payment_links", "ck_payment_links_status", "status IN ('active','used','expired','cancelled')")

    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_payment_gateways_tenant ON public.dbp_payment_gateways (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_payment_transactions_tenant_status ON public.dbp_payment_transactions (tenant_id, status, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_payment_transactions_reference ON public.dbp_payment_transactions (tenant_id, reference_type, reference_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_payment_links_tenant_status ON public.dbp_payment_links (tenant_id, status, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_payment_links_expiry ON public.dbp_payment_links (expires_at)")

    _enable_tenant_rls("dbp_payment_gateways")
    _enable_tenant_rls("dbp_payment_transactions")
    _enable_tenant_rls("dbp_payment_links")


def downgrade() -> None:
    for table in ("dbp_payment_links", "dbp_payment_transactions", "dbp_payment_gateways"):
        op.execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table}" ON public.{table}')
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS public.dbp_payment_links")
    op.execute("DROP TABLE IF EXISTS public.dbp_payment_transactions")
    op.execute("DROP TABLE IF EXISTS public.dbp_payment_gateways")
