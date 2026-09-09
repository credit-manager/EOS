"""Persist MFA verification state on rotating refresh sessions.

Revision ID: 20260910_refresh_mfa_state
Revises: 20260910_builder_ddl_hardening
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_refresh_mfa_state"
down_revision = "20260910_builder_ddl_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dbp_refresh_tokens",
        sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "idx_dbp_refresh_tokens_mfa_state",
        "dbp_refresh_tokens",
        ["user_id", "tenant_id", "mfa_verified", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_dbp_refresh_tokens_mfa_state", table_name="dbp_refresh_tokens")
    op.drop_column("dbp_refresh_tokens", "mfa_verified")
