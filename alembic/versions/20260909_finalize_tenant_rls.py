"""Finalize tenant RLS after the complete canonical schema exists.

Revision ID: 20260909_finalize_tenant_rls
Revises: 20260909_merge_release_heads

The release head runs after schema restoration and normalizes tenant isolation
for every public base table that actually has a tenant_id column. The dynamic
scan prevents newly-added tenant tables from silently escaping the RLS contract.
"""

from alembic import op

revision = "20260909_finalize_tenant_rls"
down_revision = "20260909_merge_release_heads"
branch_labels = None
depends_on = None

TENANT_SCOPED_TABLES = (
    "dbp_entities", "dbp_fields", "dbp_relationships", "dbp_entity_versions",
    "dbp_row_rules", "dbp_events", "dbp_webhooks", "dbp_webhook_deliveries",
    "dbp_notifications", "dbp_notification_templates", "dbp_notification_preferences",
    "dbp_dashboards", "dbp_dashboard_widgets", "dbp_kpis",
    "dbp_workflow_definitions", "dbp_workflow_states", "dbp_workflow_transitions",
    "dbp_workflow_instances", "dbp_workflow_actions", "dbp_data_jobs",
    "dbp_validation_rules", "dbp_companies", "dbp_branches", "dbp_departments",
    "dbp_fiscal_years", "dbp_currencies", "dbp_cost_centers", "dbp_accounts",
    "dbp_journal_entries", "dbp_journal_lines", "dbp_tenant_lifecycle_events",
    "dbp_tenant_data_exports", "dbp_tenant_invitations", "dbp_tenant_activity_logs",
    "dbp_tenant_notifications", "dbp_construction_projects",
    "dbp_construction_daily_reports", "dbp_construction_materials",
    "dbp_construction_equipment", "dbp_construction_workers", "dbp_construction_safety",
    "dbp_construction_subcontractors", "dbp_trading_customers", "dbp_trading_items",
    "dbp_trading_stock", "dbp_trading_suppliers", "dbp_trading_warehouses",
    "dbp_retail_stores", "dbp_retail_products", "dbp_retail_transactions",
    "dbp_restaurant_menu", "dbp_restaurant_orders", "dbp_restaurant_tables",
    "dbp_manufacturing_bom", "dbp_manufacturing_work_orders",
    "dbp_manufacturing_operations", "dbp_services_catalog", "dbp_services_orders",
    "dbp_saas_features", "dbp_saas_usage", "dbp_notify_channels",
    "dbp_approve_workflows", "dbp_docs_categories", "dbp_docs_files", "dbp_custom_configs",
)


def _migration_block(down: bool = False) -> str:
    tables_sql = ", ".join("%r" % table for table in TENANT_SCOPED_TABLES)
    if down:
        return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN information_schema.columns AS cols
                  ON cols.table_schema = n.nspname
                 AND cols.table_name = c.relname
                 AND cols.column_name = 'tenant_id'
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND c.relname = ANY(ARRAY[{tables_sql}]::text[])
            LOOP
                v_policy_name := 'tenant_isolation_' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', v_table_name);
            END LOOP;
        END $$;
        """

    return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN information_schema.columns AS cols
                  ON cols.table_schema = n.nspname
                 AND cols.table_name = c.relname
                 AND cols.column_name = 'tenant_id'
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND (
                      c.relname = ANY(ARRAY[{tables_sql}]::text[])
                      OR c.relname LIKE 'dbp_%'
                  )
            LOOP
                v_policy_name := 'tenant_isolation_' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format(
                    'CREATE POLICY %I ON public.%I ' ||
                    'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
                    'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                    v_policy_name, v_table_name
                );
            END LOOP;
        END $$;
        """


def upgrade() -> None:
    op.execute(_migration_block())


def downgrade() -> None:
    op.execute(_migration_block(down=True))
