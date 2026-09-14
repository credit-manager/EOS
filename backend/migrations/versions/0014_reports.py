"""reports analytics engine

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("entity_code", sa.String(length=100), nullable=False),
        sa.Column("metric", sa.String(length=20), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("conditions_json", sa.Text(), nullable=True),
        sa.Column("group_by", sa.String(length=100), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_analytics_report_tenant_code"),
    )
    op.create_index("ix_analytics_reports_tenant_id", "analytics_reports", ["tenant_id"])

    op.create_table(
        "report_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("analytics_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_runs_tenant_time", "report_runs", ["tenant_id", "created_at"])
    op.create_index("ix_report_runs_report", "report_runs", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_report_runs_report")
    op.drop_index("ix_report_runs_tenant_time")
    op.drop_table("report_runs")
    op.drop_index("ix_analytics_reports_tenant_id")
    op.drop_table("analytics_reports")