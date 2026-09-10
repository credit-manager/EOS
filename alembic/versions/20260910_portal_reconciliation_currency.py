"""Move portal, reconciliation and currency schemas into Alembic-owned DDL."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_portal_reconciliation_currency"
down_revision = "20260910_rate_limits"
branch_labels = None
depends_on = None


def _create(bind, table_name, columns, constraints=None):
    if not sa.inspect(bind).has_table(table_name, schema="public"):
        op.create_table(
            table_name,
            *columns,
            *(constraints or []),
            schema="public",
        )


def upgrade() -> None:
    bind = op.get_bind()

    _create(bind, "dbp_portal_users", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("last_login", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_portal_sessions", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("session_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("session_token", name="uq_dbp_portal_sessions_token"),
    ])
    _create(bind, "dbp_portal_notifications", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false()),
        sa.Column("link", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])

    _create(bind, "dbp_bank_accounts", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("company_id", sa.Text()),
        sa.Column("account_name", sa.Text(), nullable=False),
        sa.Column("bank_name", sa.Text()),
        sa.Column("account_number", sa.Text()),
        sa.Column("iban", sa.Text()),
        sa.Column("currency", sa.Text(), server_default="SAR"),
        sa.Column("opening_balance", sa.Numeric(15, 2), server_default="0"),
        sa.Column("current_balance", sa.Numeric(15, 2), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_bank_statements", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("bank_account_id", sa.Text(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(15, 2), nullable=False),
        sa.Column("closing_balance", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending"),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_bank_statement_lines", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("statement_id", sa.Text(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("debit", sa.Numeric(15, 2), server_default="0"),
        sa.Column("credit", sa.Numeric(15, 2), server_default="0"),
        sa.Column("balance", sa.Numeric(15, 2), server_default="0"),
        sa.Column("reference", sa.Text()),
        sa.Column("matched_transaction_id", sa.Text()),
        sa.Column("match_status", sa.Text(), server_default="unmatched"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_reconciliation_logs", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("bank_account_id", sa.Text(), nullable=False),
        sa.Column("statement_id", sa.Text()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column("reconciled_by", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])

    _create(bind, "dbp_currencies", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_ar", sa.Text()),
        sa.Column("symbol", sa.Text()),
        sa.Column("decimal_places", sa.Integer(), server_default="2"),
        sa.Column("is_base", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_exchange_rates", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("from_currency", sa.Text(), nullable=False),
        sa.Column("to_currency", sa.Text(), nullable=False),
        sa.Column("rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("source", sa.Text(), server_default="manual"),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])
    _create(bind, "dbp_currency_transactions", [
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("transaction_id", sa.Text()),
        sa.Column("original_currency", sa.Text(), nullable=False),
        sa.Column("original_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("base_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("gain_loss", sa.Numeric(15, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    ])


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in (
        "dbp_currency_transactions", "dbp_exchange_rates", "dbp_currencies",
        "dbp_reconciliation_logs", "dbp_bank_statement_lines", "dbp_bank_statements",
        "dbp_bank_accounts", "dbp_portal_notifications", "dbp_portal_sessions",
        "dbp_portal_users",
    ):
        if sa.inspect(bind).has_table(table_name, schema="public"):
            op.drop_table(table_name, schema="public")
