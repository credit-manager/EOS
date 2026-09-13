"""Add updated_at timestamp to all models

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Auth tables
    op.add_column('tenants', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('tenant_memberships', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('auth_sessions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    
    # Financial tables
    op.add_column('financial_accounts', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('financial_journal_entries', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('financial_journal_lines', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('financial_journal_lines', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    
    # Metadata tables
    op.add_column('metadata_entities', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    
    # Workflow tables
    op.add_column('workflow_definitions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('workflow_approval_tasks', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('workflow_approval_tasks', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    
    # Audit tables
    op.add_column('audit_events', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    # Audit tables
    op.drop_column('audit_events', 'updated_at')
    
    # Workflow tables
    op.drop_column('workflow_approval_tasks', 'updated_at')
    op.drop_column('workflow_approval_tasks', 'created_at')
    op.drop_column('workflow_definitions', 'updated_at')
    
    # Metadata tables
    op.drop_column('metadata_entities', 'updated_at')
    
    # Financial tables
    op.drop_column('financial_journal_lines', 'updated_at')
    op.drop_column('financial_journal_lines', 'created_at')
    op.drop_column('financial_journal_entries', 'updated_at')
    op.drop_column('financial_accounts', 'updated_at')
    
    # Auth tables
    op.drop_column('auth_sessions', 'updated_at')
    op.drop_column('tenant_memberships', 'updated_at')
    op.drop_column('users', 'updated_at')
    op.drop_column('tenants', 'updated_at')
