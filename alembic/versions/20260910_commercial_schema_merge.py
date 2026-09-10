"""Reconcile historical schema branches and enforce financial invariants.

This unreleased commercial merge is the single release head. It reconciles
the two historical lineages, hardens double-entry constraints, and adds
DB-backed idempotency for payment creation.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_commercial_schema_merge"
down_revision = ("20260910_refresh_mfa_state", "20260905_restore_api_core_tables")
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("dbp_journal_lines", schema="public"):
        raise RuntimeError("dbp_journal_lines is required before commercial financial hardening")

    invalid = bind.execute(sa.text(
        "SELECT COUNT(*) FROM public.dbp_journal_lines "
        "WHERE debit < 0 OR credit < 0 OR (debit = 0 AND credit = 0) "
        "OR (debit > 0 AND credit > 0)"
    )).scalar()
    if invalid:
        raise RuntimeError(f"Refusing release migration: {invalid} invalid journal line(s) exist")

    existing = {c["name"] for c in inspector.get_check_constraints("dbp_journal_lines", schema="public")}
    if "ck_dbp_journal_lines_non_negative" not in existing:
        op.create_check_constraint(
            "ck_dbp_journal_lines_non_negative",
            "dbp_journal_lines",
            "debit >= 0 AND credit >= 0",
        )
    if "ck_dbp_journal_lines_exactly_one_side" not in existing:
        op.create_check_constraint(
            "ck_dbp_journal_lines_exactly_one_side",
            "dbp_journal_lines",
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
        )

    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("dbp_payment_transactions", schema="public")}
    if "idempotency_key_hash" not in columns:
        op.add_column(
            "dbp_payment_transactions",
            sa.Column("idempotency_key_hash", sa.String(64), nullable=True),
        )
    if "idempotency_fingerprint" not in columns:
        op.add_column(
            "dbp_payment_transactions",
            sa.Column("idempotency_fingerprint", sa.String(64), nullable=True),
        )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_payment_transactions_idempotency "
        "ON public.dbp_payment_transactions (tenant_id, idempotency_key_hash) "
        "WHERE idempotency_key_hash IS NOT NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("dbp_payment_transactions", schema="public"):
        op.execute("DROP INDEX IF EXISTS public.uq_dbp_payment_transactions_idempotency")
        columns = {c["name"] for c in inspector.get_columns("dbp_payment_transactions", schema="public")}
        if "idempotency_fingerprint" in columns:
            op.drop_column("dbp_payment_transactions", "idempotency_fingerprint")
        if "idempotency_key_hash" in columns:
            op.drop_column("dbp_payment_transactions", "idempotency_key_hash")

    inspector = sa.inspect(bind)
    if inspector.has_table("dbp_journal_lines", schema="public"):
        existing = {c["name"] for c in inspector.get_check_constraints("dbp_journal_lines", schema="public")}
        if "ck_dbp_journal_lines_exactly_one_side" in existing:
            op.drop_constraint("ck_dbp_journal_lines_exactly_one_side", "dbp_journal_lines", type_="check")
        if "ck_dbp_journal_lines_non_negative" in existing:
            op.drop_constraint("ck_dbp_journal_lines_non_negative", "dbp_journal_lines", type_="check")
