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


# Tables that should have RLS enabled (tenant-scoped)
# NOTE: Identity/platform tables are EXCLUDED from RLS:
#   - dbp_users: queried during login BEFORE auth (no tenant context)
#   - dbp_saas_tenants: platform-level table, not tenant-scoped
#   - dbp_saas_plans: platform-level table, not tenant-scoped
TENANT_SCOPED_TABLES = [
    # Core metadata
    'dbp_entities',
    'dbp_fields',
    'dbp_relationships',
    'dbp_entity_versions',
    'dbp_row_rules',
    'dbp_events',
    'dbp_webhooks',
    'dbp_webhook_deliveries',
    
    # Notifications
    'dbp_notifications',
    'dbp_notification_templates',
    'dbp_notification_preferences',
    
    # Dashboards
    'dbp_dashboards',
    'dbp_dashboard_widgets',
    'dbp_kpis',
    
    # Workflows
    'dbp_workflow_definitions',
    'dbp_workflow_states',
    'dbp_workflow_transitions',
    'dbp_workflow_instances',
    'dbp_workflow_actions',
    
    # Data jobs
    'dbp_data_jobs',
    
    # Validation
    'dbp_validation_rules',
    
    # ERP Foundation
    'dbp_companies',
    'dbp_branches',
    'dbp_departments',
    'dbp_fiscal_years',
    'dbp_currencies',
    'dbp_cost_centers',
    
    # Users — NOT protected by RLS (identity table, queried during login)
    # 'dbp_users' is intentionally excluded
    
    # Accounts / Accounting
    'dbp_accounts',
    'dbp_journal_entries',
    'dbp_journal_lines',
    
    # Tenant lifecycle
    'dbp_tenant_lifecycle_events',
    'dbp_tenant_data_exports',
    'dbp_tenant_invitations',
    'dbp_tenant_activity_logs',
    'dbp_tenant_notifications',
    
    # Industry packs
    'dbp_construction_projects',
    'dbp_construction_daily_reports',
    'dbp_construction_materials',
    'dbp_construction_equipment',
    'dbp_construction_workers',
    'dbp_construction_safety',
    'dbp_construction_subcontractors',
    
    # Trading
    'dbp_trading_customers',
    'dbp_trading_items',
    'dbp_trading_stock',
    'dbp_trading_suppliers',
    'dbp_trading_warehouses',
    
    # Retail
    'dbp_retail_stores',
    'dbp_retail_products',
    'dbp_retail_transactions',
    
    # Restaurant
    'dbp_restaurant_menu',
    'dbp_restaurant_orders',
    'dbp_restaurant_tables',
    
    # Manufacturing
    'dbp_manufacturing_bom',
    'dbp_manufacturing_work_orders',
    'dbp_manufacturing_operations',
    
    # Services
    'dbp_services_catalog',
    'dbp_services_orders',
    
    # SaaS — platform-level tables, NOT tenant-scoped
    # 'dbp_saas_tenants' and 'dbp_saas_plans' intentionally excluded
    'dbp_saas_features',
    'dbp_saas_usage',
    
    # Notifications / Approvals / Docs
    'dbp_notify_channels',
    'dbp_approve_workflows',
    'dbp_docs_categories',
    'dbp_docs_files',
    
    # Custom
    'dbp_custom_configs',
]


def upgrade() -> None:
    conn = op.get_bind()
    
    for table_name in TENANT_SCOPED_TABLES:
        try:
            # 1. Enable RLS on the table
            conn.execute(sa.text(
                f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"
            ))
            
            # 2. Force RLS for table owner (prevents bypass)
            conn.execute(sa.text(
                f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"
            ))
            
            # 3. Drop existing policy if any
            conn.execute(sa.text(
                f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"
            ))
            
            # 4. Create tenant isolation policy
            conn.execute(sa.text(f"""
                CREATE POLICY tenant_isolation ON {table_name}
                USING (tenant_id = current_setting('app.tenant_id', true))
            """))
            
        except Exception as e:
            # Log but continue — some tables may not exist yet
            print(f"RLS skipped for {table_name}: {e}")


def downgrade() -> None:
    conn = op.get_bind()
    
    for table_name in TENANT_SCOPED_TABLES:
        try:
            # Drop policy
            conn.execute(sa.text(
                f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}"
            ))
            
            # Disable RLS
            conn.execute(sa.text(
                f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"
            ))
            
        except Exception as e:
            print(f"RLS rollback skipped for {table_name}: {e}")
