"""activate row-level security on all tenant-scoped tables

Revision ID: rls_activate_001
Revises: idx_perf_001
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'rls_activate_001'
down_revision = 'idx_perf_001'
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = [
    'dbp_entities', 'dbp_fields', 'dbp_relationships',
    'dbp_entity_versions', 'dbp_row_rules', 'dbp_events',
    'dbp_webhooks', 'dbp_webhook_deliveries',
    'dbp_notifications', 'dbp_notification_templates', 'dbp_notification_preferences',
    'dbp_dashboards', 'dbp_dashboard_widgets', 'dbp_kpis',
    'dbp_workflow_definitions', 'dbp_workflow_states',
    'dbp_workflow_transitions', 'dbp_workflow_instances', 'dbp_workflow_actions',
    'dbp_data_jobs', 'dbp_validation_rules',
    'dbp_companies', 'dbp_branches', 'dbp_departments',
    'dbp_fiscal_years', 'dbp_currencies', 'dbp_cost_centers',
    'dbp_accounts', 'dbp_journal_entries', 'dbp_journal_lines',
    'dbp_tenant_lifecycle_events', 'dbp_tenant_data_exports',
    'dbp_tenant_invitations', 'dbp_tenant_activity_logs', 'dbp_tenant_notifications',
    'dbp_construction_projects', 'dbp_construction_daily_reports',
    'dbp_construction_materials', 'dbp_construction_equipment',
    'dbp_construction_workers', 'dbp_construction_safety', 'dbp_construction_subcontractors',
    'dbp_trading_customers', 'dbp_trading_items', 'dbp_trading_stock',
    'dbp_trading_suppliers', 'dbp_trading_warehouses',
    'dbp_retail_stores', 'dbp_retail_products', 'dbp_retail_transactions',
    'dbp_restaurant_menu', 'dbp_restaurant_orders', 'dbp_restaurant_tables',
    'dbp_manufacturing_bom', 'dbp_manufacturing_work_orders', 'dbp_manufacturing_operations',
    'dbp_services_catalog', 'dbp_services_orders',
    'dbp_saas_features', 'dbp_saas_usage',
    'dbp_notify_channels', 'dbp_approve_workflows',
    'dbp_docs_categories', 'dbp_docs_files',
    'dbp_custom_configs',
]


def _table_exists(conn, table_name):
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = :t"
    ), {"t": table_name}).fetchone()
    return result is not None


def _column_exists(conn, table_name, column_name):
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
    ), {"t": table_name, "c": column_name}).fetchone()
    return result is not None


def upgrade() -> None:
    conn = op.get_bind()

    for table_name in TENANT_SCOPED_TABLES:
        if not _table_exists(conn, table_name):
            continue

        has_tenant = _column_exists(conn, table_name, 'tenant_id')
        if not has_tenant:
            continue

        try:
            conn.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        except Exception:
            pass

        try:
            conn.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
        except Exception:
            pass

        try:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"))
        except Exception:
            pass

        if has_tenant:
            try:
                conn.execute(sa.text(f"""
                    CREATE POLICY tenant_isolation ON {table_name}
                    USING (tenant_id::text = current_setting('app.tenant_id', true))
                """))
            except Exception:
                pass


def downgrade() -> None:
    conn = op.get_bind()

    for table_name in TENANT_SCOPED_TABLES:
        if not _table_exists(conn, table_name):
            continue

        try:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"))
        except Exception:
            pass

        try:
            conn.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
        except Exception:
            pass
