"""Add CRM tables.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd5e6f7a8b9c0'
down_revision: str | Sequence[str] | None = 'c4d5e6f7a8b9'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('crm_contacts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('first_name', sa.String(100), nullable=False),
    sa.Column('last_name', sa.String(100), nullable=False),
    sa.Column('email', sa.String(255), nullable=False),
    sa.Column('phone', sa.String(50), nullable=True),
    sa.Column('company', sa.String(200), nullable=True),
    sa.Column('job_title', sa.String(200), nullable=True),
    sa.Column('lead_source', sa.String(100), nullable=True),
    sa.Column('status', sa.String(30), nullable=False, server_default='lead'),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('lead', 'prospect', 'customer', 'inactive')", name='ck_crm_contact_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'email', name='uq_crm_contact_tenant_email')
    )
    op.create_index(op.f('ix_crm_contacts_tenant_id'), 'crm_contacts', ['tenant_id'], unique=False)
    op.create_index('ix_crm_contact_tenant_status', 'crm_contacts', ['tenant_id', 'status'], unique=False)

    op.create_table('crm_opportunities',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(200), nullable=False),
    sa.Column('value', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
    sa.Column('stage', sa.String(30), nullable=False, server_default='prospecting'),
    sa.Column('probability', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('expected_close_date', sa.Date(), nullable=True),
    sa.Column('assigned_to', sa.Uuid(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("stage IN ('prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost')", name='ck_crm_opportunity_stage'),
    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_opportunities_tenant_id'), 'crm_opportunities', ['tenant_id'], unique=False)
    op.create_index('ix_crm_opportunity_tenant_stage', 'crm_opportunities', ['tenant_id', 'stage'], unique=False)

    op.create_table('crm_activities',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=False),
    sa.Column('opportunity_id', sa.Uuid(), nullable=True),
    sa.Column('activity_type', sa.String(20), nullable=False),
    sa.Column('subject', sa.String(200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("activity_type IN ('call', 'email', 'meeting', 'task')", name='ck_crm_activity_type'),
    sa.CheckConstraint("status IN ('pending', 'completed', 'cancelled')", name='ck_crm_activity_status'),
    sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['opportunity_id'], ['crm_opportunities.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_activities_tenant_id'), 'crm_activities', ['tenant_id'], unique=False)
    op.create_index('ix_crm_activity_tenant_contact', 'crm_activities', ['tenant_id', 'contact_id'], unique=False)

    op.create_table('crm_notes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('contact_id', sa.Uuid(), nullable=False),
    sa.Column('opportunity_id', sa.Uuid(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['contact_id'], ['crm_contacts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['opportunity_id'], ['crm_opportunities.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_notes_tenant_id'), 'crm_notes', ['tenant_id'], unique=False)
    op.create_index('ix_crm_note_tenant_contact', 'crm_notes', ['tenant_id', 'contact_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_crm_note_tenant_contact', table_name='crm_notes')
    op.drop_index(op.f('ix_crm_notes_tenant_id'), table_name='crm_notes')
    op.drop_table('crm_notes')
    op.drop_index('ix_crm_activity_tenant_contact', table_name='crm_activities')
    op.drop_index(op.f('ix_crm_activities_tenant_id'), table_name='crm_activities')
    op.drop_table('crm_activities')
    op.drop_index('ix_crm_opportunity_tenant_stage', table_name='crm_opportunities')
    op.drop_index(op.f('ix_crm_opportunities_tenant_id'), table_name='crm_opportunities')
    op.drop_table('crm_opportunities')
    op.drop_index('ix_crm_contact_tenant_status', table_name='crm_contacts')
    op.drop_index(op.f('ix_crm_contacts_tenant_id'), table_name='crm_contacts')
    op.drop_table('crm_contacts')
