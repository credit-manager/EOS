"""Compatibility migration for refresh-token schema restoration.

The preceding ``20260905_refresh_tokens`` migration already creates the
runtime refresh-token table on every fresh database. This revision is kept as
the canonical Alembic head for environments that already recorded the
restoration revision; it must therefore not attempt to create or drop the same
table a second time.
"""

revision = "20260905_restore_refresh_tokens"
down_revision = "20260905_restore_auth_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The table is created by 20260905_refresh_tokens.
    pass


def downgrade() -> None:
    # Keep the earlier migration's ownership of dbp_refresh_tokens intact.
    pass
