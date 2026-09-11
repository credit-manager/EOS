import sqlalchemy as sa
from alembic import op

revision = "0007_record_workflow_link"
down_revision = "0006_workflow_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "records",
        sa.Column("workflow_instance_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_records_workflow_instance_id",
        "records",
        ["workflow_instance_id"],
    )
    op.create_foreign_key(
        "fk_records_workflow_instance_id",
        "records",
        "workflow_instances",
        ["workflow_instance_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_records_workflow_instance_id", "records", type="foreignkey")
    op.drop_index("ix_records_workflow_instance_id", table_name="records")
    op.drop_column("records", "workflow_instance_id")
