"""Add project financial accounts table.

Revision ID: b27fc19bcac3
Revises: 0008_construction_full
Create Date: 2026-09-11 22:18:15.771809
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b27fc19bcac3'
down_revision: str | Sequence[str] | None = '0008_construction_full'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "construction_project_financial_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("cash_account_id", sa.Uuid(), nullable=False),
        sa.Column("accounts_receivable_account_id", sa.Uuid(), nullable=False),
        sa.Column("accounts_payable_account_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_account_id", sa.Uuid(), nullable=False),
        sa.Column("grni_account_id", sa.Uuid(), nullable=False),
        sa.Column("materials_account_id", sa.Uuid(), nullable=False),
        sa.Column("construction_revenue_account_id", sa.Uuid(), nullable=False),
        sa.Column("labor_account_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_account_id", sa.Uuid(), nullable=False),
        sa.Column("subcontractor_account_id", sa.Uuid(), nullable=False),
        sa.Column("overhead_account_id", sa.Uuid(), nullable=False),
        sa.Column("wip_account_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), onupdate=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("tenant_id IS NOT NULL", name="ck_financial_accounts_tenant"),
        sa.CheckConstraint("project_id IS NOT NULL", name="ck_financial_accounts_project"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", name="uq_project_financial_accounts_tenant_project"),
    )
    op.create_index(
        op.f("ix_construction_project_financial_accounts_tenant_id"),
        "construction_project_financial_accounts",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_construction_project_financial_accounts_project_id"),
        "construction_project_financial_accounts",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_construction_project_financial_accounts_project_id"), table_name="construction_project_financial_accounts")
    op.drop_index(op.f("ix_construction_project_financial_accounts_tenant_id"), table_name="construction_project_financial_accounts")
    op.drop_table("construction_project_financial_accounts")
