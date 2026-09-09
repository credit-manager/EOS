"""Add rotating opaque refresh-token storage for production sessions."""
from alembic import op
import sqlalchemy as sa

revision = "20260905_refresh_tokens"
down_revision = "20260905_sales_crm_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dbp_refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(100), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("family_id", sa.String(36), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_dbp_refresh_tokens_active",
        "dbp_refresh_tokens",
        ["user_id", "tenant_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_dbp_refresh_tokens_active", table_name="dbp_refresh_tokens")
    op.drop_table("dbp_refresh_tokens")
