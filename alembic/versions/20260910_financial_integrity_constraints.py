"""Enforce database-level invariants for double-entry journal lines.

Application validation is useful but insufficient for a commercial ERP: direct
SQL, alternate workers, imports, or future endpoints must not be able to store
an invalid journal line.  The migration deliberately fails on pre-existing
invalid rows instead of silently changing financial data.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_financial_integrity_constraints"
down_revision = "20260910_commercial_schema_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("dbp_journal_lines", schema="public"):
        raise RuntimeError("dbp_journal_lines is required before financial integrity constraints")

    invalid = bind.execute(sa.text(
        "SELECT COUNT(*) FROM public.dbp_journal_lines "
        "WHERE debit < 0 OR credit < 0 OR (debit = 0 AND credit = 0) "
        "OR (debit > 0 AND credit > 0)"
    )).scalar()
    if invalid:
        raise RuntimeError(
            f"Refusing financial migration: {invalid} invalid journal line(s) exist"
        )

    op.create_check_constraint(
        "ck_dbp_journal_lines_non_negative",
        "dbp_journal_lines",
        "debit >= 0 AND credit >= 0",
    )
    op.create_check_constraint(
        "ck_dbp_journal_lines_exactly_one_side",
        "dbp_journal_lines",
        "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_dbp_journal_lines_exactly_one_side",
        "dbp_journal_lines",
        type_="check",
    )
    op.drop_constraint(
        "ck_dbp_journal_lines_non_negative",
        "dbp_journal_lines",
        type_="check",
    )
