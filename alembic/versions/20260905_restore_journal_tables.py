"""Restore general-ledger journal tables required by Sales accounting."""
from alembic import op
import sqlalchemy as sa

revision = "20260905_restore_journal_tables"
down_revision = "20260905_number_sequences"
branch_labels = None
depends_on = None


def _rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table}" ON {table}')
    op.execute(
        f'''CREATE POLICY "tenant_isolation_{table}" ON {table}
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))'''
    )


def upgrade() -> None:
    op.create_table(
        "dbp_journal_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("fiscal_year_id", sa.String(36), nullable=True),
        sa.Column("entry_number", sa.String(64), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False, server_default="standard"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("is_posted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_debit", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("total_credit", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "company_id", "entry_number", name="uq_dbp_journal_entries_tenant_company_number"),
    )
    op.create_index("ix_dbp_journal_entries_tenant_id", "dbp_journal_entries", ["tenant_id"])
    op.create_index("ix_dbp_journal_entries_company_id", "dbp_journal_entries", ["company_id"])
    op.create_index("ix_dbp_journal_entries_reference", "dbp_journal_entries", ["tenant_id", "company_id", "reference"])

    op.create_table(
        "dbp_journal_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("journal_entry_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("debit", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost_center_id", sa.String(36), nullable=True),
        sa.Column("line_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("debit >= 0", name="ck_dbp_journal_lines_debit_nonnegative"),
        sa.CheckConstraint("credit >= 0", name="ck_dbp_journal_lines_credit_nonnegative"),
        sa.CheckConstraint("debit > 0 OR credit > 0", name="ck_dbp_journal_lines_nonzero"),
    )
    op.create_index("ix_dbp_journal_lines_entry_id", "dbp_journal_lines", ["journal_entry_id"])
    op.create_index("ix_dbp_journal_lines_account_id", "dbp_journal_lines", ["account_id"])

    _rls("dbp_journal_entries")
    # Journal lines do not carry tenant_id; access is constrained through the
    # tenant-scoped parent entry in application code.


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "tenant_isolation_dbp_journal_entries" ON dbp_journal_entries')
    op.execute("ALTER TABLE dbp_journal_entries NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dbp_journal_entries DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_dbp_journal_lines_account_id", table_name="dbp_journal_lines")
    op.drop_index("ix_dbp_journal_lines_entry_id", table_name="dbp_journal_lines")
    op.drop_table("dbp_journal_lines")
    op.drop_index("ix_dbp_journal_entries_reference", table_name="dbp_journal_entries")
    op.drop_index("ix_dbp_journal_entries_company_id", table_name="dbp_journal_entries")
    op.drop_index("ix_dbp_journal_entries_tenant_id", table_name="dbp_journal_entries")
    op.drop_table("dbp_journal_entries")
