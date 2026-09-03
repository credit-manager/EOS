"""Create the application rate-limit store.

Schema is managed by Alembic rather than created at application startup.
"""
from alembic import op

revision = "20260902_rate_limit_store"
down_revision = "20260901_tenant_entity_codes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS dbp_rate_limits (
        bucket TEXT PRIMARY KEY,
        window_start TIMESTAMP NOT NULL,
        request_count INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT ck_dbp_rate_limits_count_nonnegative CHECK (request_count >= 0)
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_rate_limits_window_start ON dbp_rate_limits (window_start)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_dbp_rate_limits_window_start")
    op.execute("DROP TABLE IF EXISTS dbp_rate_limits")
