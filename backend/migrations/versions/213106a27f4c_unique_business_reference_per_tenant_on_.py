"""unique business reference per tenant on journal entries.

Revision ID: 213106a27f4c
Revises: b27fc19bcac3
Create Date: 2026-09-12 11:04:00.632342
"""
from collections.abc import Sequence

from alembic import op

revision: str = '213106a27f4c'
down_revision: str | Sequence[str] | None = 'b27fc19bcac3'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Enforces posting idempotency at the database level: one journal entry
    # per (tenant_id, reference). NULL references stay exempt because NULLs
    # are distinct in unique constraints on both PostgreSQL and SQLite.
    with op.batch_alter_table("financial_journal_entries") as batch_op:
        batch_op.create_unique_constraint(
            "uq_financial_journal_tenant_reference",
            ["tenant_id", "reference"],
        )


def downgrade() -> None:
    with op.batch_alter_table("financial_journal_entries") as batch_op:
        batch_op.drop_constraint(
            "uq_financial_journal_tenant_reference", type_="unique"
        )
