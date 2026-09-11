"""add explicit double-entry financial core"""
import sqlalchemy as sa
from alembic import op

revision = "0005_financial_core"
down_revision = "0004_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_financial_account_tenant_code"),
    )
    op.create_index("ix_financial_accounts_tenant_id", "financial_accounts", ["tenant_id"])

    op.create_table(
        "financial_journal_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("entry_number", sa.Integer(), nullable=False),
        sa.Column("accounting_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "entry_number", name="uq_financial_journal_tenant_number"),
    )
    op.create_index("ix_financial_journal_entries_tenant_id", "financial_journal_entries", ["tenant_id"])
    op.create_index("ix_financial_journal_entries_entry_number", "financial_journal_entries", ["entry_number"])
    op.create_index("ix_financial_journal_entries_accounting_date", "financial_journal_entries", ["accounting_date"])
    op.create_index("ix_financial_journal_entries_status", "financial_journal_entries", ["status"])

    op.create_table(
        "financial_journal_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journal_entry_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("debit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["account_id"], ["financial_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["financial_journal_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_journal_lines_journal_entry_id", "financial_journal_lines", ["journal_entry_id"])
    op.create_index("ix_financial_journal_lines_account_id", "financial_journal_lines", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_financial_journal_lines_account_id", table_name="financial_journal_lines")
    op.drop_index("ix_financial_journal_lines_journal_entry_id", table_name="financial_journal_lines")
    op.drop_table("financial_journal_lines")
    op.drop_index("ix_financial_journal_entries_status", table_name="financial_journal_entries")
    op.drop_index("ix_financial_journal_entries_accounting_date", table_name="financial_journal_entries")
    op.drop_index("ix_financial_journal_entries_entry_number", table_name="financial_journal_entries")
    op.drop_index("ix_financial_journal_entries_tenant_id", table_name="financial_journal_entries")
    op.drop_table("financial_journal_entries")
    op.drop_index("ix_financial_accounts_tenant_id", table_name="financial_accounts")
    op.drop_table("financial_accounts")
