"""Restore core API tables required by authentication and accounting APIs.

The canonical initial migration records historical schema state but does not create
these legacy API tables on a fresh PostgreSQL database. Keep the repair additive so
existing production databases are unaffected and fresh CI databases become runnable.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_restore_api_core_tables"
down_revision = "20260905_force_tenant_rls"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dbp_companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_dbp_companies_tenant_code"),
    )

    op.create_table(
        "dbp_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), nullable=False, index=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=True),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=True, server_default="SAR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("opening_balance", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("current_balance", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "company_id", "code", name="uq_dbp_accounts_tenant_company_code"),
    )


def downgrade():
    op.drop_table("dbp_accounts")
    op.drop_table("dbp_companies")
