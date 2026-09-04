"""Create core accounting tables used by the accounting engine.

The original initial migration did not include these tables even though the
accounting API depends on them. Keep the schema explicit and migration-safe.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260902_accounting_schema"
down_revision = "314bc1528464"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dbp_accounts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=True),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("currency_code", sa.String(10), nullable=False),
        sa.Column("opening_balance", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("current_balance", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["company_id"], ["dbp_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["dbp_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "company_id", "code", name="uq_dbp_accounts_tenant_company_code"),
    )
    op.create_index("ix_dbp_accounts_tenant_id", "dbp_accounts", ["tenant_id"])
    op.create_index("ix_dbp_accounts_company_id", "dbp_accounts", ["company_id"])
    op.create_index("ix_dbp_accounts_code", "dbp_accounts", ["code"])

    op.create_table(
        "dbp_journal_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("fiscal_year_id", sa.String(36), nullable=True),
        sa.Column("entry_number", sa.String(100), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_debit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("total_credit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("is_posted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["company_id"], ["dbp_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fiscal_year_id"], ["dbp_fiscal_years.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "company_id", "entry_number", name="uq_dbp_journal_entries_tenant_company_number"),
    )
    op.create_index("ix_dbp_journal_entries_tenant_id", "dbp_journal_entries", ["tenant_id"])
    op.create_index("ix_dbp_journal_entries_company_id", "dbp_journal_entries", ["company_id"])
    op.create_index("ix_dbp_journal_entries_status", "dbp_journal_entries", ["status"])
    op.create_index("ix_dbp_journal_entries_entry_date", "dbp_journal_entries", ["entry_date"])

    op.create_table(
        "dbp_journal_lines",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("journal_entry_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("debit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost_center_id", sa.String(36), nullable=True),
        sa.Column("line_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["dbp_journal_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["dbp_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cost_center_id"], ["dbp_cost_centers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dbp_journal_lines_journal_entry_id", "dbp_journal_lines", ["journal_entry_id"])
    op.create_index("ix_dbp_journal_lines_account_id", "dbp_journal_lines", ["account_id"])

    op.create_table(
        "number_sequences",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("current_number", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("increment_by", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("padding", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_number_sequences_tenant_name"),
    )
    op.create_index("ix_number_sequences_tenant_id", "number_sequences", ["tenant_id"])


def downgrade():
    op.drop_index("ix_number_sequences_tenant_id", table_name="number_sequences")
    op.drop_table("number_sequences")
    op.drop_index("ix_dbp_journal_lines_account_id", table_name="dbp_journal_lines")
    op.drop_index("ix_dbp_journal_lines_journal_entry_id", table_name="dbp_journal_lines")
    op.drop_table("dbp_journal_lines")
    op.drop_index("ix_dbp_journal_entries_entry_date", table_name="dbp_journal_entries")
    op.drop_index("ix_dbp_journal_entries_status", table_name="dbp_journal_entries")
    op.drop_index("ix_dbp_journal_entries_company_id", table_name="dbp_journal_entries")
    op.drop_index("ix_dbp_journal_entries_tenant_id", table_name="dbp_journal_entries")
    op.drop_table("dbp_journal_entries")
    op.drop_index("ix_dbp_accounts_code", table_name="dbp_accounts")
    op.drop_index("ix_dbp_accounts_company_id", table_name="dbp_accounts")
    op.drop_index("ix_dbp_accounts_tenant_id", table_name="dbp_accounts")
    op.drop_table("dbp_accounts")
