"""add critical performance indexes

Revision ID: idx_perf_001
Revises: 87aba7990b4d
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'idx_perf_001'
down_revision = '87aba7990b4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────
    # AUTH / USER INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_users_email', 'dbp_users', ['email'], unique=True)
    op.create_index('ix_dbp_users_tenant_id', 'dbp_users', ['tenant_id'])
    op.create_index('ix_dbp_users_tenant_email', 'dbp_users', ['tenant_id', 'email'])
    
    # ──────────────────────────────────────────────────────────────
    # ACCOUNTING INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_accounts_tenant_company', 'dbp_accounts', ['tenant_id', 'company_id'])
    op.create_index('ix_dbp_accounts_company_code', 'dbp_accounts', ['company_id', 'code'])
    op.create_index('ix_dbp_journal_entries_company_status', 'dbp_journal_entries', ['company_id', 'status'])
    op.create_index('ix_dbp_journal_entries_tenant_id', 'dbp_journal_entries', ['tenant_id'])
    op.create_index('ix_dbp_journal_lines_entry_id', 'dbp_journal_lines', ['journal_entry_id'])
    
    # ──────────────────────────────────────────────────────────────
    # WORKFLOW INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_workflow_instances_status', 'dbp_workflow_instances', ['status'])
    op.create_index('ix_dbp_workflow_instances_tenant_status', 'dbp_workflow_instances', ['tenant_id', 'status'])
    op.create_index('ix_dbp_workflow_instances_entity_record', 'dbp_workflow_instances', ['entity_code', 'record_id'])
    op.create_index('ix_dbp_workflow_actions_instance_id', 'dbp_workflow_actions', ['instance_id'])
    
    # ──────────────────────────────────────────────────────────────
    # NOTIFICATION INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_notifications_user_read', 'dbp_notifications', ['user_id', 'is_read'])
    op.create_index('ix_dbp_notifications_tenant_user', 'dbp_notifications', ['tenant_id', 'user_id'])
    
    # ──────────────────────────────────────────────────────────────
    # ENTITY / METADATA INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_entities_code', 'dbp_entities', ['code'], unique=True)
    op.create_index('ix_dbp_fields_entity_id', 'dbp_fields', ['entity_id'])
    op.create_index('ix_dbp_relationships_entity_id', 'dbp_relationships', ['entity_id'])
    
    # ──────────────────────────────────────────────────────────────
    # DASHBOARD INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_dashboards_tenant_id', 'dbp_dashboards', ['tenant_id'])
    op.create_index('ix_dbp_dashboard_widgets_dashboard_id', 'dbp_dashboard_widgets', ['dashboard_id'])
    
    # ──────────────────────────────────────────────────────────────
    # COMPANY / ORG INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_companies_tenant_id', 'dbp_companies', ['tenant_id'])
    op.create_index('ix_dbp_branches_company_id', 'dbp_branches', ['company_id'])
    op.create_index('ix_dbp_departments_company_id', 'dbp_departments', ['company_id'])
    op.create_index('ix_dbp_departments_tenant_id', 'dbp_departments', ['tenant_id'])
    
    # ──────────────────────────────────────────────────────────────
    # VALIDATION RULES INDEXES
    # ──────────────────────────────────────────────────────────────
    op.create_index('ix_dbp_validation_rules_entity_id', 'dbp_validation_rules', ['entity_id'])
    op.create_index('ix_dbp_validation_rules_tenant_entity', 'dbp_validation_rules', ['tenant_id', 'entity_id'])


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_dbp_validation_rules_tenant_entity', table_name='dbp_validation_rules')
    op.drop_index('ix_dbp_validation_rules_entity_id', table_name='dbp_validation_rules')
    op.drop_index('ix_dbp_departments_tenant_id', table_name='dbp_departments')
    op.drop_index('ix_dbp_departments_company_id', table_name='dbp_departments')
    op.drop_index('ix_dbp_branches_company_id', table_name='dbp_branches')
    op.drop_index('ix_dbp_companies_tenant_id', table_name='dbp_companies')
    op.drop_index('ix_dbp_dashboard_widgets_dashboard_id', table_name='dbp_dashboard_widgets')
    op.drop_index('ix_dbp_dashboards_tenant_id', table_name='dbp_dashboards')
    op.drop_index('ix_dbp_relationships_entity_id', table_name='dbp_relationships')
    op.drop_index('ix_dbp_fields_entity_id', table_name='dbp_fields')
    op.drop_index('ix_dbp_entities_code', table_name='dbp_entities')
    op.drop_index('ix_dbp_notifications_tenant_user', table_name='dbp_notifications')
    op.drop_index('ix_dbp_notifications_user_read', table_name='dbp_notifications')
    op.drop_index('ix_dbp_workflow_actions_instance_id', table_name='dbp_workflow_actions')
    op.drop_index('ix_dbp_workflow_instances_entity_record', table_name='dbp_workflow_instances')
    op.drop_index('ix_dbp_workflow_instances_tenant_status', table_name='dbp_workflow_instances')
    op.drop_index('ix_dbp_workflow_instances_status', table_name='dbp_workflow_instances')
    op.drop_index('ix_dbp_journal_lines_entry_id', table_name='dbp_journal_lines')
    op.drop_index('ix_dbp_journal_entries_tenant_id', table_name='dbp_journal_entries')
    op.drop_index('ix_dbp_journal_entries_company_status', table_name='dbp_journal_entries')
    op.drop_index('ix_dbp_accounts_company_code', table_name='dbp_accounts')
    op.drop_index('ix_dbp_accounts_tenant_company', table_name='dbp_accounts')
    op.drop_index('ix_dbp_users_tenant_email', table_name='dbp_users')
    op.drop_index('ix_dbp_users_tenant_id', table_name='dbp_users')
    op.drop_index('ix_dbp_users_email', table_name='dbp_users')
