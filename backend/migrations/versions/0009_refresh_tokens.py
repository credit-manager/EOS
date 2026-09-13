"""Add refresh token columns to auth_sessions

Revision ID: 0009
Revises: 213106a27f4c
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '213106a27f4c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('auth_sessions') as batch_op:
        batch_op.add_column(sa.Column('refresh_token_hash', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('refresh_expires_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint('uq_auth_session_refresh_token', ['refresh_token_hash'])
        batch_op.create_index('ix_auth_sessions_refresh_token_hash', ['refresh_token_hash'])


def downgrade() -> None:
    with op.batch_alter_table('auth_sessions') as batch_op:
        batch_op.drop_index('ix_auth_sessions_refresh_token_hash')
        batch_op.drop_constraint('uq_auth_session_refresh_token', type_='unique')
        batch_op.drop_column('refresh_expires_at')
        batch_op.drop_column('refresh_token_hash')
