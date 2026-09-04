"""Reliability primitives: idempotency keys and transactional outbox."""
from alembic import op
import sqlalchemy as sa

revision = "20260904_reliability_foundation"
down_revision = "20260904_model_alignment"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table: str):
    policy = f"tenant_isolation_{table}"
    op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON public."{table}"')
    op.execute(f'''CREATE POLICY "{policy}" ON public."{table}"
        USING (tenant_id::text = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))''')


def _disable_tenant_rls(table: str):
    policy = f"tenant_isolation_{table}"
    op.execute(f'DROP POLICY IF EXISTS "{policy}" ON public."{table}"')
    op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')


def upgrade():
    op.create_table("dbp_idempotency_keys",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("key", sa.String(255), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True), sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "key", name="uq_dbp_idempotency_tenant_key"))
    op.create_index("ix_dbp_idempotency_tenant_created", "dbp_idempotency_keys", ["tenant_id", "created_at"])
    op.create_table("dbp_outbox_events",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False), sa.Column("aggregate_type", sa.String(120), nullable=False),
        sa.Column("aggregate_id", sa.String(120), nullable=False), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "event_type", "aggregate_type", "aggregate_id", name="uq_dbp_outbox_event"))
    op.create_index("ix_dbp_outbox_pending", "dbp_outbox_events", ["status", "available_at", "created_at"])
    op.create_index("ix_dbp_outbox_tenant_created", "dbp_outbox_events", ["tenant_id", "created_at"])
    _enable_tenant_rls("dbp_idempotency_keys")
    _enable_tenant_rls("dbp_outbox_events")


def downgrade():
    _disable_tenant_rls("dbp_outbox_events")
    _disable_tenant_rls("dbp_idempotency_keys")
    op.drop_index("ix_dbp_outbox_tenant_created", table_name="dbp_outbox_events")
    op.drop_index("ix_dbp_outbox_pending", table_name="dbp_outbox_events")
    op.drop_table("dbp_outbox_events")
    op.drop_index("ix_dbp_idempotency_tenant_created", table_name="dbp_idempotency_keys")
    op.drop_table("dbp_idempotency_keys")
