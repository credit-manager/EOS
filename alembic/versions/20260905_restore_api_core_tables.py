"""Restore core API tables required by authentication and accounting APIs.

The legacy initial migration does not create these API tables on a fresh
PostgreSQL database. This additive migration restores the runtime contract for
fresh environments without changing existing production rows.
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
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_dbp_companies_tenant_code"),
    )
    op.create_index("ix_dbp_companies_tenant_id", "dbp_companies", ["tenant_id"])

    op.create_table(
        "dbp_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
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
    op.create_index("ix_dbp_accounts_tenant_id", "dbp_accounts", ["tenant_id"])
    op.create_index("ix_dbp_accounts_company_id", "dbp_accounts", ["company_id"])


def downgrade():
    op.drop_index("ix_dbp_accounts_company_id", table_name="dbp_accounts")
    op.drop_index("ix_dbp_accounts_tenant_id", table_name="dbp_accounts")
    op.drop_table("dbp_accounts")
    op.drop_index("ix_dbp_companies_tenant_id", table_name="dbp_companies")
    op.drop_table("dbp_companies")
