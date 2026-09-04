"""Align live schema with the current ORM metadata after tenant hardening."""
from alembic import op
import sqlalchemy as sa

revision = "20260904_model_alignment"
down_revision = "20260902_acct_posting"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "dbp_currencies", "dbp_dashboards", "dbp_data_jobs", "dbp_entities",
    "dbp_events", "dbp_kpis", "dbp_notification_preferences",
    "dbp_notification_templates", "dbp_notifications", "dbp_validation_rules",
    "dbp_webhooks", "dbp_workflow_definitions", "dbp_workflow_instances",
)


def upgrade():
    # Existing installations may contain legacy NULL tenant values. Normalize
    # them before enforcing the ORM's non-null tenant contract.
    for table in TENANT_TABLES:
        op.execute(sa.text(f"UPDATE {table} SET tenant_id = 'platform' WHERE tenant_id IS NULL"))
        op.alter_column(table, "tenant_id", existing_type=sa.String(length=36), nullable=False)

    # Entity codes are tenant-independent in the current canonical model.
    op.execute("DROP INDEX IF EXISTS uq_dbp_entities_global_code")
    op.execute("DROP INDEX IF EXISTS uq_dbp_entities_tenant_code")
    op.create_index("ix_dbp_entities_code", "dbp_entities", ["code"], unique=True)


def downgrade():
    op.drop_index("ix_dbp_entities_code", table_name="dbp_entities")
    op.create_index("uq_dbp_entities_tenant_code", "dbp_entities", ["tenant_id", "code"], unique=True)
    for table in reversed(TENANT_TABLES):
        op.alter_column(table, "tenant_id", existing_type=sa.String(length=36), nullable=True)
