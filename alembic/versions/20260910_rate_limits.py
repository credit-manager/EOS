"""Create the shared PostgreSQL rate-limit bucket table."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_rate_limits"
down_revision = "20260910_commercial_schema_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dbp_rate_limits",
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("bucket", name="pk_dbp_rate_limits"),
        schema="public",
    )
    op.create_index(
        "ix_dbp_rate_limits_window_start",
        "dbp_rate_limits",
        ["window_start"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_dbp_rate_limits_window_start", table_name="dbp_rate_limits", schema="public")
    op.drop_table("dbp_rate_limits", schema="public")
