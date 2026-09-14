"""rules

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=True),
        sa.Column("actions_json", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rules_tenant_event_type", "rules", ["tenant_id", "event_type"])
    op.create_index("ix_rules_tenant_id", "rules", ["tenant_id"])

    op.create_table(
        "rule_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_event_id", sa.Uuid(), sa.ForeignKey("system_events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rule_executions_tenant_time", "rule_executions", ["tenant_id", "executed_at"])
    op.create_index("ix_rule_executions_rule", "rule_executions", ["rule_id"])
    op.create_index("ix_rule_executions_event", "rule_executions", ["triggered_event_id"])


def downgrade() -> None:
    op.drop_index("ix_rule_executions_event")
    op.drop_index("ix_rule_executions_rule")
    op.drop_index("ix_rule_executions_tenant_time")
    op.drop_table("rule_executions")
    op.drop_index("ix_rules_tenant_id")
    op.drop_index("ix_rules_tenant_event_type")
    op.drop_table("rules")