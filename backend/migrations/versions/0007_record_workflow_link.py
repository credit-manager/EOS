import sqlalchemy as sa
from alembic import op

revision = "0007_record_workflow_link"
down_revision = "0006_workflow_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("records") as batch_op:
        batch_op.add_column(sa.Column("workflow_instance_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_records_workflow_instance_id", ["workflow_instance_id"])
        batch_op.create_foreign_key(
            "fk_records_workflow_instance_id",
            "workflow_instances",
            ["workflow_instance_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("records") as batch_op:
        batch_op.drop_constraint("fk_records_workflow_instance_id", type_="foreignkey")
        batch_op.drop_index("ix_records_workflow_instance_id")
        batch_op.drop_column("workflow_instance_id")
