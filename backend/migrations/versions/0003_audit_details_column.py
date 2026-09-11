"""rename audit metadata column to details to match ORM semantics"""
import sqlalchemy as sa
from alembic import op

revision = "0003_audit_details_column"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("audit_events")}
    if "metadata" in columns and "details" not in columns:
        with op.batch_alter_table("audit_events") as batch_op:
            batch_op.alter_column("metadata", new_column_name="details")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("audit_events")}
    if "details" in columns and "metadata" not in columns:
        with op.batch_alter_table("audit_events") as batch_op:
            batch_op.alter_column("details", new_column_name="metadata")
