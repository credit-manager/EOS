"""Add construction industry pack tables.

Revision ID: 0008_construction_core
Revises: 0007_record_workflow_link
Create Date: 2026-09-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_construction_core"
down_revision = "0007_record_workflow_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "construction_projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="planning",
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "budget", sa.Numeric(15, 2), nullable=False, server_default="0"
        ),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "code", name="uq_construction_project_tenant_code"
        ),
        sa.CheckConstraint(
            "status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')",
            name="ck_construction_project_status",
        ),
    )
    op.create_index(
        "ix_construction_projects_tenant_id", "construction_projects", ["tenant_id"]
    )
    op.create_index(
        "ix_construction_project_tenant_status",
        "construction_projects",
        ["tenant_id", "status"],
    )

    op.create_table(
        "construction_contracts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("construction_projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contract_number", sa.String(50), nullable=False),
        sa.Column(
            "contract_type",
            sa.String(30),
            nullable=False,
            server_default="main",
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("counterparty", sa.String(200), nullable=False),
        sa.Column(
            "contract_value",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="draft"
        ),
        sa.Column("signed_date", sa.Date(), nullable=True),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "contract_number",
            name="uq_construction_contract_tenant_number",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_approval', 'active', 'completed', 'terminated')",
            name="ck_construction_contract_status",
        ),
        sa.CheckConstraint(
            "contract_type IN ('main', 'subcontract', 'supply')",
            name="ck_construction_contract_type",
        ),
    )
    op.create_index(
        "ix_construction_contracts_tenant_id", "construction_contracts", ["tenant_id"]
    )
    op.create_index(
        "ix_construction_contract_project",
        "construction_contracts",
        ["project_id"],
    )

    op.create_table(
        "construction_boqs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            sa.Uuid(),
            sa.ForeignKey("construction_contracts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="draft"
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "contract_id", "version", name="uq_construction_boq_version"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved')",
            name="ck_construction_boq_status",
        ),
    )
    op.create_index(
        "ix_construction_boqs_tenant_id", "construction_boqs", ["tenant_id"]
    )

    op.create_table(
        "construction_boq_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "boq_id",
            sa.Uuid(),
            sa.ForeignKey("construction_boqs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("item_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_rate", sa.Numeric(15, 2), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_construction_boq_items_tenant_id",
        "construction_boq_items",
        ["tenant_id"],
    )
    op.create_index(
        "ix_construction_boq_item_boq", "construction_boq_items", ["boq_id"]
    )

    op.create_table(
        "construction_progress_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            sa.Uuid(),
            sa.ForeignKey("construction_contracts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("claim_number", sa.String(50), nullable=False),
        sa.Column("claim_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="draft"
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "claim_number",
            name="uq_construction_claim_tenant_number",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'paid')",
            name="ck_construction_claim_status",
        ),
    )
    op.create_index(
        "ix_construction_progress_claims_tenant_id",
        "construction_progress_claims",
        ["tenant_id"],
    )

    op.create_table(
        "construction_progress_claim_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            sa.Uuid(),
            sa.ForeignKey(
                "construction_progress_claims.id", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "boq_item_id",
            sa.Uuid(),
            sa.ForeignKey("construction_boq_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity_completed", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_construction_progress_claim_lines_tenant_id",
        "construction_progress_claim_lines",
        ["tenant_id"],
    )
    op.create_index(
        "ix_construction_claim_line_claim",
        "construction_progress_claim_lines",
        ["claim_id"],
    )

    op.create_table(
        "construction_procurements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("construction_projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requisition_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "requested_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="draft"
        ),
        sa.Column(
            "priority", sa.String(20), nullable=False, server_default="medium"
        ),
        sa.Column(
            "total_estimated",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "requisition_number",
            name="uq_construction_procurement_tenant_number",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'ordered', 'received', 'cancelled')",
            name="ck_construction_procurement_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_construction_procurement_priority",
        ),
    )
    op.create_index(
        "ix_construction_procurements_tenant_id",
        "construction_procurements",
        ["tenant_id"],
    )

    op.create_table(
        "construction_procurement_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "procurement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "construction_procurements.id", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("estimated_unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("estimated_total", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_construction_procurement_lines_tenant_id",
        "construction_procurement_lines",
        ["tenant_id"],
    )
    op.create_index(
        "ix_construction_procurement_line_parent",
        "construction_procurement_lines",
        ["procurement_id"],
    )


def downgrade() -> None:
    op.drop_table("construction_procurement_lines")
    op.drop_table("construction_procurements")
    op.drop_table("construction_progress_claim_lines")
    op.drop_table("construction_progress_claims")
    op.drop_table("construction_boq_items")
    op.drop_table("construction_boqs")
    op.drop_table("construction_contracts")
    op.drop_table("construction_projects")
