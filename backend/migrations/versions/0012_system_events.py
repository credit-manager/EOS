"""system_events

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_events_tenant_id", "system_events", ["tenant_id"])
    op.create_index("ix_system_events_event_type", "system_events", ["event_type"])
    op.create_index(
        "ix_system_events_tenant_occurred", "system_events", ["tenant_id", "occurred_at"]
    )
    op.create_index(
        "ix_system_events_entity", "system_events", ["tenant_id", "entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_system_events_entity")
    op.drop_index("ix_system_events_tenant_occurred")
    op.drop_index("ix_system_events_event_type")
    op.drop_index("ix_system_events_tenant_id")
    op.drop_table("system_events")