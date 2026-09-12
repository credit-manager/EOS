"""Add all construction industry pack tables.

Revision ID: 0008_construction_full
Revises: 0007_record_workflow_link
Create Date: 2026-09-11
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008_construction_full'
down_revision: str | Sequence[str] | None = '0007_record_workflow_link'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ### Core Construction Tables ###
    op.create_table('construction_projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(50), nullable=False),
    sa.Column('name', sa.String(200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(30), nullable=False, server_default='planning'),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('budget', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('client_name', sa.String(200), nullable=True),
    sa.Column('location', sa.String(500), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')", name='ck_construction_project_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'code', name='uq_construction_project_tenant_code')
    )
    op.create_index(op.f('ix_construction_projects_tenant_id'), 'construction_projects', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_project_tenant_status'), 'construction_projects', ['tenant_id', 'status'], unique=False)

    op.create_table('construction_contracts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('contract_number', sa.String(50), nullable=False),
    sa.Column('contract_type', sa.String(30), nullable=False, server_default='main'),
    sa.Column('title', sa.String(200), nullable=False),
    sa.Column('counterparty', sa.String(200), nullable=False),
    sa.Column('contract_value', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('signed_date', sa.Date(), nullable=True),
    sa.Column('completion_date', sa.Date(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("contract_type IN ('main', 'subcontract', 'supply')", name='ck_construction_contract_type'),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'active', 'completed', 'terminated')", name='ck_construction_contract_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'contract_number', name='uq_construction_contract_tenant_number')
    )
    op.create_index(op.f('ix_construction_contracts_tenant_id'), 'construction_contracts', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_contract_project'), 'construction_contracts', ['project_id'], unique=False)

    op.create_table('construction_boqs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'approved')", name='ck_construction_boq_status'),
    sa.ForeignKeyConstraint(['contract_id'], ['construction_contracts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'contract_id', 'version', name='uq_construction_boq_version')
    )
    op.create_index(op.f('ix_construction_boqs_tenant_id'), 'construction_boqs', ['tenant_id'], unique=False)

    op.create_table('construction_boq_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('boq_id', sa.Uuid(), nullable=False),
    sa.Column('item_number', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('unit', sa.String(20), nullable=False),
    sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
    sa.Column('unit_rate', sa.Numeric(15, 2), nullable=False),
    sa.Column('amount', sa.Numeric(15, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['boq_id'], ['construction_boqs.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_construction_boq_items_tenant_id'), 'construction_boq_items', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_boq_item_boq'), 'construction_boq_items', ['boq_id'], unique=False)

    op.create_table('construction_budgets',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'approved', 'baselined')", name='ck_construction_budget_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'project_id', 'version', name='uq_construction_budget_version')
    )
    op.create_index(op.f('ix_construction_budgets_tenant_id'), 'construction_budgets', ['tenant_id'], unique=False)

    op.create_table('construction_budget_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('budget_id', sa.Uuid(), nullable=False),
    sa.Column('boq_item_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('unit', sa.String(20), nullable=False),
    sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
    sa.Column('unit_rate', sa.Numeric(15, 2), nullable=False),
    sa.Column('amount', sa.Numeric(15, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['boq_item_id'], ['construction_boq_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['budget_id'], ['construction_budgets.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_construction_budget_lines_tenant_id'), 'construction_budget_lines', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_budget_line_budget'), 'construction_budget_lines', ['budget_id'], unique=False)

    op.create_table('construction_progress_claims',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('claim_number', sa.String(50), nullable=False),
    sa.Column('claim_date', sa.Date(), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'approved', 'paid')", name='ck_construction_claim_status'),
    sa.ForeignKeyConstraint(['contract_id'], ['construction_contracts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'claim_number', name='uq_construction_claim_tenant_number')
    )
    op.create_index(op.f('ix_construction_progress_claims_tenant_id'), 'construction_progress_claims', ['tenant_id'], unique=False)

    op.create_table('construction_progress_claim_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=False),
    sa.Column('boq_item_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('quantity_completed', sa.Numeric(12, 2), nullable=False),
    sa.Column('amount', sa.Numeric(15, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['boq_item_id'], ['construction_boq_items.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['claim_id'], ['construction_progress_claims.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_construction_progress_claim_lines_tenant_id'), 'construction_progress_claim_lines', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_claim_line_claim'), 'construction_progress_claim_lines', ['claim_id'], unique=False)

    op.create_table('construction_change_orders',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('change_order_number', sa.String(50), nullable=False),
    sa.Column('title', sa.String(200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('impact_type', sa.String(20), nullable=False, server_default='cost'),
    sa.Column('cost_impact', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('time_impact_days', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('requested_by', sa.Uuid(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("impact_type IN ('cost', 'time', 'both')", name='ck_construction_change_order_impact'),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'approved', 'rejected', 'implemented')", name='ck_construction_change_order_status'),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['contract_id'], ['construction_contracts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'change_order_number', name='uq_construction_change_order_number')
    )
    op.create_index(op.f('ix_construction_change_orders_tenant_id'), 'construction_change_orders', ['tenant_id'], unique=False)

    op.create_table('construction_subcontracts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('subcontract_number', sa.String(50), nullable=False),
    sa.Column('subcontractor_name', sa.String(200), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('value', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'active', 'completed', 'terminated')", name='ck_construction_subcontract_status'),
    sa.ForeignKeyConstraint(['contract_id'], ['construction_contracts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'subcontract_number', name='uq_construction_subcontract_number')
    )
    op.create_index(op.f('ix_construction_subcontracts_tenant_id'), 'construction_subcontracts', ['tenant_id'], unique=False)

    op.create_table('construction_site_warehouses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(50), nullable=False),
    sa.Column('name', sa.String(200), nullable=False),
    sa.Column('location', sa.String(500), nullable=True),
    sa.Column('manager_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'code', name='uq_construction_warehouse_tenant_code')
    )
    op.create_index(op.f('ix_construction_site_warehouses_tenant_id'), 'construction_site_warehouses', ['tenant_id'], unique=False)

    op.create_table('construction_procurements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('requisition_number', sa.String(50), nullable=False),
    sa.Column('title', sa.String(200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('requested_by', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
    sa.Column('total_estimated', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='ck_construction_procurement_priority'),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'approved', 'ordered', 'received', 'invoiced', 'paid', 'cancelled')", name='ck_construction_procurement_status'),
    sa.ForeignKeyConstraint(['project_id'], ['construction_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'requisition_number', name='uq_construction_procurement_tenant_number')
    )
    op.create_index(op.f('ix_construction_procurements_tenant_id'), 'construction_procurements', ['tenant_id'], unique=False)

    op.create_table('construction_procurement_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('procurement_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('unit', sa.String(20), nullable=False),
    sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
    sa.Column('estimated_unit_price', sa.Numeric(15, 2), nullable=False),
    sa.Column('estimated_total', sa.Numeric(15, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['procurement_id'], ['construction_procurements.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_construction_procurement_lines_tenant_id'), 'construction_procurement_lines', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_construction_procurement_line_parent'), 'construction_procurement_lines', ['procurement_id'], unique=False)

    # ### Procurement Workflow Tables ###
    op.create_table('construction_purchase_orders',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('procurement_id', sa.Uuid(), nullable=False),
    sa.Column('supplier_id', sa.Uuid(), nullable=False),
    sa.Column('po_number', sa.String(50), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
    sa.Column('terms', sa.Text(), nullable=True),
    sa.Column('delivery_date', sa.Date(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'sent', 'acknowledged', 'partial_received', 'received', 'cancelled')", name='ck_construction_po_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['procurement_id'], ['construction_procurements.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'po_number', name='uq_construction_po_tenant_number')
    )
    op.create_index(op.f('ix_construction_purchase_orders_tenant_id'), 'construction_purchase_orders', ['tenant_id'], unique=False)

    op.create_table('construction_purchase_order_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('procurement_line_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('unit', sa.String(20), nullable=False),
    sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
    sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
    sa.Column('line_total', sa.Numeric(15, 2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['procurement_line_id'], ['construction_procurement_lines.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['construction_purchase_orders.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_construction_po_line_parent', 'construction_purchase_order_lines', ['purchase_order_id'], unique=False)
    op.create_index(op.f('ix_construction_purchase_order_lines_tenant_id'), 'construction_purchase_order_lines', ['tenant_id'], unique=False)

    op.create_table('construction_goods_receipts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('grn_number', sa.String(50), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('received_date', sa.Date(), nullable=False),
    sa.Column('warehouse_id', sa.Uuid(), nullable=False),
    sa.Column('received_by', sa.Uuid(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'partial', 'completed', 'cancelled')", name='ck_construction_grn_status'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['construction_purchase_orders.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['received_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['construction_site_warehouses.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'grn_number', name='uq_construction_grn_tenant_number')
    )
    op.create_index(op.f('ix_construction_goods_receipts_tenant_id'), 'construction_goods_receipts', ['tenant_id'], unique=False)

    op.create_table('construction_goods_receipt_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('goods_receipt_id', sa.Uuid(), nullable=False),
    sa.Column('po_line_id', sa.Uuid(), nullable=False),
    sa.Column('quantity_received', sa.Numeric(12, 2), nullable=False),
    sa.Column('quantity_accepted', sa.Numeric(12, 2), nullable=False),
    sa.Column('quantity_rejected', sa.Numeric(12, 2), nullable=False, server_default='0'),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['goods_receipt_id'], ['construction_goods_receipts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['po_line_id'], ['construction_purchase_order_lines.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_construction_goods_receipt_lines_tenant_id'), 'construction_goods_receipt_lines', ['tenant_id'], unique=False)
    op.create_index('ix_construction_grn_line_parent', 'construction_goods_receipt_lines', ['goods_receipt_id'], unique=False)

    op.create_table('construction_supplier_invoices',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('grn_id', sa.Uuid(), nullable=True),
    sa.Column('invoice_number', sa.String(50), nullable=False),
    sa.Column('supplier_invoice_number', sa.String(100), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('invoice_date', sa.Date(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
    sa.Column('subtotal', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('tax_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('submitted_by', sa.Uuid(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'approved', 'paid', 'rejected', 'cancelled')", name='ck_construction_invoice_status'),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['grn_id'], ['construction_goods_receipts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['construction_purchase_orders.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'invoice_number', name='uq_construction_invoice_tenant_number')
    )
    op.create_index(op.f('ix_construction_supplier_invoices_tenant_id'), 'construction_supplier_invoices', ['tenant_id'], unique=False)

    op.create_table('construction_payments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('supplier_invoice_id', sa.Uuid(), nullable=False),
    sa.Column('payment_number', sa.String(50), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('payment_method', sa.String(20), nullable=False, server_default='bank_transfer'),
    sa.Column('amount', sa.Numeric(15, 2), nullable=False),
    sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
    sa.Column('payment_date', sa.Date(), nullable=False),
    sa.Column('reference', sa.String(200), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("payment_method IN ('bank_transfer', 'check', 'cash', 'card', 'other')", name='ck_construction_payment_method'),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'approved', 'processing', 'completed', 'failed', 'cancelled')", name='ck_construction_payment_status'),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supplier_invoice_id'], ['construction_supplier_invoices.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'payment_number', name='uq_construction_payment_tenant_number')
    )
    op.create_index(op.f('ix_construction_payments_tenant_id'), 'construction_payments', ['tenant_id'], unique=False)

    op.create_table('construction_supplier_invoice_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('supplier_invoice_id', sa.Uuid(), nullable=False),
    sa.Column('grn_line_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.String(500), nullable=False),
    sa.Column('unit', sa.String(20), nullable=False),
    sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
    sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
    sa.Column('line_total', sa.Numeric(15, 2), nullable=False),
    sa.Column('tax_rate', sa.Numeric(5, 2), nullable=False, server_default='0'),
    sa.Column('tax_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['grn_line_id'], ['construction_goods_receipt_lines.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['supplier_invoice_id'], ['construction_supplier_invoices.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_construction_invoice_line_parent', 'construction_supplier_invoice_lines', ['supplier_invoice_id'], unique=False)
    op.create_index(op.f('ix_construction_supplier_invoice_lines_tenant_id'), 'construction_supplier_invoice_lines', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_construction_supplier_invoice_lines_tenant_id'), table_name='construction_supplier_invoice_lines')
    op.drop_index('ix_construction_invoice_line_parent', table_name='construction_supplier_invoice_lines')
    op.drop_table('construction_supplier_invoice_lines')
    op.drop_index(op.f('ix_construction_payments_tenant_id'), table_name='construction_payments')
    op.drop_table('construction_payments')
    op.drop_index(op.f('ix_construction_supplier_invoices_tenant_id'), table_name='construction_supplier_invoices')
    op.drop_table('construction_supplier_invoices')
    op.drop_index('ix_construction_grn_line_parent', table_name='construction_goods_receipt_lines')
    op.drop_index(op.f('ix_construction_goods_receipt_lines_tenant_id'), table_name='construction_goods_receipt_lines')
    op.drop_table('construction_goods_receipt_lines')
    op.drop_index(op.f('ix_construction_goods_receipts_tenant_id'), table_name='construction_goods_receipts')
    op.drop_table('construction_goods_receipts')
    op.drop_index(op.f('ix_construction_purchase_order_lines_tenant_id'), table_name='construction_purchase_order_lines')
    op.drop_index('ix_construction_po_line_parent', table_name='construction_purchase_order_lines')
    op.drop_table('construction_purchase_order_lines')
    op.drop_index(op.f('ix_construction_purchase_orders_tenant_id'), table_name='construction_purchase_orders')
    op.drop_table('construction_purchase_orders')
    op.drop_index(op.f('ix_construction_procurement_lines_tenant_id'), table_name='construction_procurement_lines')
    op.drop_index(op.f('ix_construction_procurement_line_parent'), table_name='construction_procurement_lines')
    op.drop_table('construction_procurement_lines')
    op.drop_index(op.f('ix_construction_procurements_tenant_id'), table_name='construction_procurements')
    op.drop_table('construction_procurements')
    op.drop_index(op.f('ix_construction_site_warehouses_tenant_id'), table_name='construction_site_warehouses')
    op.drop_table('construction_site_warehouses')
    op.drop_index(op.f('ix_construction_subcontracts_tenant_id'), table_name='construction_subcontracts')
    op.drop_table('construction_subcontracts')
    op.drop_index(op.f('ix_construction_change_orders_tenant_id'), table_name='construction_change_orders')
    op.drop_table('construction_change_orders')
    op.drop_index(op.f('ix_construction_progress_claim_lines_tenant_id'), table_name='construction_progress_claim_lines')
    op.drop_index(op.f('ix_construction_claim_line_claim'), table_name='construction_progress_claim_lines')
    op.drop_table('construction_progress_claim_lines')
    op.drop_index(op.f('ix_construction_progress_claims_tenant_id'), table_name='construction_progress_claims')
    op.drop_table('construction_progress_claims')
    op.drop_index(op.f('ix_construction_budget_lines_tenant_id'), table_name='construction_budget_lines')
    op.drop_index(op.f('ix_construction_budget_line_budget'), table_name='construction_budget_lines')
    op.drop_table('construction_budget_lines')
    op.drop_index(op.f('ix_construction_budgets_tenant_id'), table_name='construction_budgets')
    op.drop_table('construction_budgets')
    op.drop_index(op.f('ix_construction_boq_items_tenant_id'), table_name='construction_boq_items')
    op.drop_index(op.f('ix_construction_boq_item_boq'), table_name='construction_boq_items')
    op.drop_table('construction_boq_items')
    op.drop_index(op.f('ix_construction_boqs_tenant_id'), table_name='construction_boqs')
    op.drop_table('construction_boqs')
    op.drop_index(op.f('ix_construction_contract_project'), table_name='construction_contracts')
    op.drop_index(op.f('ix_construction_contracts_tenant_id'), table_name='construction_contracts')
    op.drop_table('construction_contracts')
    op.drop_index(op.f('ix_construction_project_tenant_status'), table_name='construction_projects')
    op.drop_index(op.f('ix_construction_projects_tenant_id'), table_name='construction_projects')
    op.drop_table('construction_projects')