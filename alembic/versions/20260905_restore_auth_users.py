"""Restore authentication users table required by the production auth API.

The historical initial schema does not create dbp_users on a fresh database,
while UserEngine and the authentication routers use it as a runtime contract.
This additive migration restores that contract for new environments.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260905_restore_auth_users"
down_revision = "20260905_restore_api_core_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dbp_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("first_name_ar", sa.String(100), nullable=True),
        sa.Column("last_name_ar", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_token_hash", sa.String(255), nullable=True),
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_token_hash", sa.String(255), nullable=True),
        sa.Column("reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_dbp_users_email"),
    )
    op.create_index("ix_dbp_users_tenant_id", "dbp_users", ["tenant_id"])


def downgrade():
    op.drop_index("ix_dbp_users_tenant_id", table_name="dbp_users")
    op.drop_table("dbp_users")
