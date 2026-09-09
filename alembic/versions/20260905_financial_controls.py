"""Financial controls: fiscal periods, accounting dimensions and exchange rates."""
from alembic import op
import sqlalchemy as sa

revision = "20260905_financial_controls"
down_revision = "20260905_reliability_foundation"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table: str):
    policy = f"tenant_isolation_{table}"
    op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE public."{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON public."{table}"')
    op.execute(f'''CREATE POLICY "{policy}" ON public."{table}"
        USING (tenant_id::text = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))''')


def _disable_tenant_rls(table: str):
    policy = f"tenant_isolation_{table}"
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON public."{table}"')
    op.execute(f'ALTER TABLE public."{table}" NO FORCE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')


def upgrade():
    op.create_table(
        "dbp_fiscal_periods",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("period_code", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("tenant_id", "company_id", "period_code", name="uq_dbp_fiscal_period"),
    )
    op.create_index("ix_dbp_fiscal_period_tenant_dates", "dbp_fiscal_periods", ["tenant_id", "company_id", "start_date", "end_date"])
    op.create_table(
        "dbp_accounting_dimensions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("dimension_type", sa.String(40), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "company_id", "dimension_type", "code", name="uq_dbp_dimension"),
    )
    op.create_table(
        "dbp_exchange_rates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("from_currency", sa.String(3), nullable=False),
        sa.Column("to_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint("tenant_id", "company_id", "rate_date", "from_currency", "to_currency", name="uq_dbp_exchange_rate"),
    )
    for table in ("dbp_fiscal_periods", "dbp_accounting_dimensions", "dbp_exchange_rates"):
        _enable_tenant_rls(table)


def downgrade():
    for table in ("dbp_exchange_rates", "dbp_accounting_dimensions", "dbp_fiscal_periods"):
        _disable_tenant_rls(table)
    op.drop_table("dbp_exchange_rates")
    op.drop_table("dbp_accounting_dimensions")
    op.drop_index("ix_dbp_fiscal_period_tenant_dates", table_name="dbp_fiscal_periods")
    op.drop_table("dbp_fiscal_periods")
