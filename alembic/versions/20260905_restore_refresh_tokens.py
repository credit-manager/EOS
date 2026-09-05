"""Restore refresh-token persistence required by production authentication.

The authentication router rotates and revokes dbp_refresh_tokens on every
login/refresh/logout flow. Fresh databases must therefore contain this table.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_restore_refresh_tokens"
down_revision = "20260905_restore_auth_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dbp_refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_dbp_refresh_tokens_token_hash"),
    )
    op.create_index("ix_dbp_refresh_tokens_user_tenant", "dbp_refresh_tokens", ["user_id", "tenant_id"])
    op.create_index("ix_dbp_refresh_tokens_family", "dbp_refresh_tokens", ["family_id"])
    op.create_index("ix_dbp_refresh_tokens_expires_at", "dbp_refresh_tokens", ["expires_at"])


def downgrade():
    op.drop_index("ix_dbp_refresh_tokens_expires_at", table_name="dbp_refresh_tokens")
    op.drop_index("ix_dbp_refresh_tokens_family", table_name="dbp_refresh_tokens")
    op.drop_index("ix_dbp_refresh_tokens_user_tenant", table_name="dbp_refresh_tokens")
    op.drop_table("dbp_refresh_tokens")
