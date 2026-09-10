"""Reconcile historical schema branches and enforce financial invariants.

This unreleased commercial merge is the single release head.  It reconciles
the two historical lineages and applies database-level journal-line checks so
financial correctness cannot depend solely on API validation.
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


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("dbp_journal_lines", schema="public"):
        existing = {c["name"] for c in inspector.get_check_constraints("dbp_journal_lines", schema="public")}
        if "ck_dbp_journal_lines_exactly_one_side" in existing:
            op.drop_constraint("ck_dbp_journal_lines_exactly_one_side", "dbp_journal_lines", type_="check")
        if "ck_dbp_journal_lines_non_negative" in existing:
            op.drop_constraint("ck_dbp_journal_lines_non_negative", "dbp_journal_lines", type_="check")
