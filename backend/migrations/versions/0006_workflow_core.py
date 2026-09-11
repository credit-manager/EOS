"""add workflow and approval core"""
import sqlalchemy as sa

from alembic import op

revision = "0006_workflow_core"
down_revision = "0005_financial_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("initial_state", sa.String(length=80), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", "version", name="uq_workflow_definition_version"),
    )
    op.create_index("ix_workflow_definitions_tenant_id", "workflow_definitions", ["tenant_id"])

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_definition_id", sa.Uuid(), nullable=False),
        sa.Column("reference_type", sa.String(length=100), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("current_state", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_workflow_instance_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_definition_id"], ["workflow_definitions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_instances_tenant_id", "workflow_instances", ["tenant_id"])
    op.create_index("ix_workflow_instances_workflow_definition_id", "workflow_instances", ["workflow_definition_id"])
    op.create_index("ix_workflow_instances_reference_id", "workflow_instances", ["reference_id"])
    op.create_index("ix_workflow_instances_current_state", "workflow_instances", ["current_state"])
    op.create_index("ix_workflow_instances_status", "workflow_instances", ["status"])

    op.create_table(
        "workflow_approval_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_instance_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=80), nullable=False),
        sa.Column("to_state", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_workflow_approval_status"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_approval_tasks_tenant_id", "workflow_approval_tasks", ["tenant_id"])
    op.create_index("ix_workflow_approval_tasks_workflow_instance_id", "workflow_approval_tasks", ["workflow_instance_id"])
    op.create_index("ix_workflow_approval_tasks_status", "workflow_approval_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_approval_tasks_status", table_name="workflow_approval_tasks")
    op.drop_index("ix_workflow_approval_tasks_workflow_instance_id", table_name="workflow_approval_tasks")
    op.drop_index("ix_workflow_approval_tasks_tenant_id", table_name="workflow_approval_tasks")
    op.drop_table("workflow_approval_tasks")
    op.drop_index("ix_workflow_instances_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_current_state", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_reference_id", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_workflow_definition_id", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_tenant_id", table_name="workflow_instances")
    op.drop_table("workflow_instances")
    op.drop_index("ix_workflow_definitions_tenant_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
