"""add critical performance indexes

Revision ID: idx_perf_001
Revises: 20260906_accounting_integrity
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'idx_perf_001'
down_revision = '20260906_accounting_integrity'
branch_labels = None
depends_on = None


def _create_index_if_not_exists(index_name, table_name, columns, unique=False, conn=None):
    """Create an index only if it doesn't already exist."""
    if conn is None:
        conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name}).fetchone()
    if result is None:
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name, conn=None):
    """Drop an index only if it exists."""
    if conn is None:
        conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name}).fetchone()
    if result is not None:
        op.drop_index(index_name)


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────
    # AUTH / USER INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_users_email', 'dbp_users', ['email'], unique=True)
    _create_index_if_not_exists('ix_dbp_users_tenant_id', 'dbp_users', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_users_tenant_email', 'dbp_users', ['tenant_id', 'email'])

    # ──────────────────────────────────────────────────────────────
    # ACCOUNTING INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_accounts_tenant_company', 'dbp_accounts', ['tenant_id', 'company_id'])
    _create_index_if_not_exists('ix_dbp_accounts_company_code', 'dbp_accounts', ['company_id', 'code'])
    _create_index_if_not_exists('ix_dbp_journal_entries_company_status', 'dbp_journal_entries', ['company_id', 'status'])
    _create_index_if_not_exists('ix_dbp_journal_entries_tenant_id', 'dbp_journal_entries', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_journal_lines_entry_id', 'dbp_journal_lines', ['journal_entry_id'])

    # ──────────────────────────────────────────────────────────────
    # WORKFLOW INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_workflow_instances_status', 'dbp_workflow_instances', ['status'])
    _create_index_if_not_exists('ix_dbp_workflow_instances_tenant_status', 'dbp_workflow_instances', ['tenant_id', 'status'])
    _create_index_if_not_exists('ix_dbp_workflow_instances_entity_record', 'dbp_workflow_instances', ['entity_code', 'record_id'])
    _create_index_if_not_exists('ix_dbp_workflow_actions_instance_id', 'dbp_workflow_actions', ['instance_id'])

    # ──────────────────────────────────────────────────────────────
    # NOTIFICATION INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_notifications_user_read', 'dbp_notifications', ['user_id', 'is_read'])
    _create_index_if_not_exists('ix_dbp_notifications_tenant_user', 'dbp_notifications', ['tenant_id', 'user_id'])

    # ──────────────────────────────────────────────────────────────
    # ENTITY / METADATA INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_entities_code', 'dbp_entities', ['code'], unique=True)
    _create_index_if_not_exists('ix_dbp_fields_entity_id', 'dbp_fields', ['entity_id'])
    _create_index_if_not_exists('ix_dbp_relationships_entity_id', 'dbp_relationships', ['entity_id'])

    # ──────────────────────────────────────────────────────────────
    # DASHBOARD INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_dashboards_tenant_id', 'dbp_dashboards', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_dashboard_widgets_dashboard_id', 'dbp_dashboard_widgets', ['dashboard_id'])

    # ──────────────────────────────────────────────────────────────
    # COMPANY / ORG INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_companies_tenant_id', 'dbp_companies', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_branches_company_id', 'dbp_branches', ['company_id'])
    _create_index_if_not_exists('ix_dbp_departments_company_id', 'dbp_departments', ['company_id'])
    _create_index_if_not_exists('ix_dbp_departments_tenant_id', 'dbp_departments', ['tenant_id'])

    # ──────────────────────────────────────────────────────────────
    # VALIDATION RULES INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_validation_rules_entity_id', 'dbp_validation_rules', ['entity_id'])
    _create_index_if_not_exists('ix_dbp_validation_rules_tenant_entity', 'dbp_validation_rules', ['tenant_id', 'entity_id'])

    # ──────────────────────────────────────────────────────────────
    # ADDITIONAL PERFORMANCE INDEXES
    # ──────────────────────────────────────────────────────────────
    _create_index_if_not_exists('ix_dbp_accounts_tenant_id', 'dbp_accounts', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_journal_lines_tenant_id', 'dbp_journal_lines', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_workflow_definitions_tenant_id', 'dbp_workflow_definitions', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_workflow_states_workflow_id', 'dbp_workflow_states', ['workflow_id'])
    _create_index_if_not_exists('ix_dbp_workflow_transitions_workflow_id', 'dbp_workflow_transitions', ['workflow_id'])
    _create_index_if_not_exists('ix_dbp_events_tenant_id', 'dbp_events', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_events_event_type', 'dbp_events', ['event_type'])
    _create_index_if_not_exists('ix_dbp_webhooks_tenant_id', 'dbp_webhooks', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_webhook_deliveries_webhook_id', 'dbp_webhook_deliveries', ['webhook_id'])
    _create_index_if_not_exists('ix_dbp_webhook_deliveries_status', 'dbp_webhook_deliveries', ['status'])
    _create_index_if_not_exists('ix_dbp_data_jobs_tenant_id', 'dbp_data_jobs', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_data_jobs_status', 'dbp_data_jobs', ['status'])
    _create_index_if_not_exists('ix_dbp_currencies_tenant_id', 'dbp_currencies', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_cost_centers_tenant_id', 'dbp_cost_centers', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_fiscal_years_tenant_id', 'dbp_fiscal_years', ['tenant_id'])
    _create_index_if_not_exists('ix_dbp_fiscal_years_company_id', 'dbp_fiscal_years', ['company_id'])
    _create_index_if_not_exists('ix_dbp_kpis_tenant_id', 'dbp_kpis', ['tenant_id'])


def downgrade() -> None:
    _drop_index_if_exists('ix_dbp_kpis_tenant_id')
    _drop_index_if_exists('ix_dbp_fiscal_years_company_id')
    _drop_index_if_exists('ix_dbp_fiscal_years_tenant_id')
    _drop_index_if_exists('ix_dbp_cost_centers_tenant_id')
    _drop_index_if_exists('ix_dbp_currencies_tenant_id')
    _drop_index_if_exists('ix_dbp_data_jobs_status')
    _drop_index_if_exists('ix_dbp_data_jobs_tenant_id')
    _drop_index_if_exists('ix_dbp_webhook_deliveries_status')
    _drop_index_if_exists('ix_dbp_webhook_deliveries_webhook_id')
    _drop_index_if_exists('ix_dbp_webhooks_tenant_id')
    _drop_index_if_exists('ix_dbp_events_event_type')
    _drop_index_if_exists('ix_dbp_events_tenant_id')
    _drop_index_if_exists('ix_dbp_workflow_transitions_workflow_id')
    _drop_index_if_exists('ix_dbp_workflow_states_workflow_id')
    _drop_index_if_exists('ix_dbp_workflow_definitions_tenant_id')
    _drop_index_if_exists('ix_dbp_journal_lines_tenant_id')
    _drop_index_if_exists('ix_dbp_accounts_tenant_id')
    _drop_index_if_exists('ix_dbp_validation_rules_tenant_entity')
    _drop_index_if_exists('ix_dbp_validation_rules_entity_id')
    _drop_index_if_exists('ix_dbp_departments_tenant_id')
    _drop_index_if_exists('ix_dbp_departments_company_id')
    _drop_index_if_exists('ix_dbp_branches_company_id')
    _drop_index_if_exists('ix_dbp_companies_tenant_id')
    _drop_index_if_exists('ix_dbp_dashboard_widgets_dashboard_id')
    _drop_index_if_exists('ix_dbp_dashboards_tenant_id')
    _drop_index_if_exists('ix_dbp_relationships_entity_id')
    _drop_index_if_exists('ix_dbp_fields_entity_id')
    _drop_index_if_exists('ix_dbp_entities_code')
    _drop_index_if_exists('ix_dbp_notifications_tenant_user')
    _drop_index_if_exists('ix_dbp_notifications_user_read')
    _drop_index_if_exists('ix_dbp_workflow_actions_instance_id')
    _drop_index_if_exists('ix_dbp_workflow_instances_entity_record')
    _drop_index_if_exists('ix_dbp_workflow_instances_tenant_status')
    _drop_index_if_exists('ix_dbp_workflow_instances_status')
    _drop_index_if_exists('ix_dbp_journal_lines_entry_id')
    _drop_index_if_exists('ix_dbp_journal_entries_tenant_id')
    _drop_index_if_exists('ix_dbp_journal_entries_company_status')
    _drop_index_if_exists('ix_dbp_accounts_company_code')
    _drop_index_if_exists('ix_dbp_accounts_tenant_company')
    _drop_index_if_exists('ix_dbp_users_tenant_email')
    _drop_index_if_exists('ix_dbp_users_tenant_id')
    _drop_index_if_exists('ix_dbp_users_email')
