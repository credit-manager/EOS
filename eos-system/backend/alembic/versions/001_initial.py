"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-08-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================================================
    # PUBLIC SCHEMA (Tenant Management)
    # =====================================================
    
    # Tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('industry', sa.String(50), nullable=False),
        sa.Column('employee_count', sa.Integer),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('subscription_plan', sa.String(50), default='basic'),
        sa.Column('subscription_expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Users table (in public schema for cross-tenant access)
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('first_name_ar', sa.String(100)),
        sa.Column('last_name_ar', sa.String(100)),
        sa.Column('phone', sa.String(50)),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Industry Templates
    op.create_table(
        'industry_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_ar', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('description_ar', sa.Text),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # =====================================================
    # TENANT SCHEMA (Per-Tenant Tables)
    # =====================================================
    
    # Note: Tenant-specific tables are created dynamically
    # when a new tenant is registered. The template is:
    
    # Accounts (Chart of Accounts)
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('accounts.id')),
        sa.Column('balance', sa.Numeric(18, 2), default=0),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Journal Entries
    op.create_table(
        'journal_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('entry_number', sa.String(50), unique=True, nullable=False),
        sa.Column('entry_date', sa.Date, nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('description_ar', sa.String(500)),
        sa.Column('total_debit', sa.Numeric(18, 2), nullable=False),
        sa.Column('total_credit', sa.Numeric(18, 2), nullable=False),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('reference', sa.String(100)),
        sa.Column('source_module', sa.String(50)),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Journal Entry Lines
    op.create_table(
        'journal_entry_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('journal_entry_id', sa.String(36), sa.ForeignKey('journal_entries.id'), nullable=False),
        sa.Column('account_id', sa.String(36), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('debit', sa.Numeric(18, 2), default=0),
        sa.Column('credit', sa.Numeric(18, 2), default=0),
        sa.Column('description', sa.String(500)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('sku', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id')),
        sa.Column('unit_price', sa.Numeric(18, 2), nullable=False),
        sa.Column('cost_price', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('current_stock', sa.Integer, default=0),
        sa.Column('min_stock', sa.Integer, default=0),
        sa.Column('max_stock', sa.Integer),
        sa.Column('barcode', sa.String(100)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Categories
    op.create_table(
        'categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('categories.id')),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Warehouses
    op.create_table(
        'warehouses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('address', sa.String(500)),
        sa.Column('address_ar', sa.String(500)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Stock Movements
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('warehouse_id', sa.String(36), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('movement_type', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_cost', sa.Numeric(18, 2)),
        sa.Column('reference', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('movement_date', sa.Date, nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Employees
    op.create_table(
        'employees',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(50), unique=True, nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('first_name_ar', sa.String(100)),
        sa.Column('last_name_ar', sa.String(100)),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50)),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id')),
        sa.Column('position_id', sa.String(36), sa.ForeignKey('positions.id')),
        sa.Column('hire_date', sa.Date, nullable=False),
        sa.Column('salary', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('national_id', sa.String(50)),
        sa.Column('social_insurance_number', sa.String(50)),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Departments
    op.create_table(
        'departments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('manager_id', sa.String(36), sa.ForeignKey('employees.id')),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('departments.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Positions
    op.create_table(
        'positions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255), nullable=False),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Customers
    op.create_table(
        'customers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255)),
        sa.Column('type', sa.String(20), default='individual'),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('address', sa.String(500)),
        sa.Column('tax_id', sa.String(50)),
        sa.Column('total_orders', sa.Integer, default=0),
        sa.Column('total_spent', sa.Numeric(18, 2), default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Leads
    op.create_table(
        'leads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('company_name', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('source', sa.String(50)),
        sa.Column('status', sa.String(20), default='new'),
        sa.Column('score', sa.Integer, default=0),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Opportunities
    op.create_table(
        'opportunities',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lead_id', sa.String(36), sa.ForeignKey('leads.id')),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('stage', sa.String(50), default='qualification'),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('expected_close_date', sa.Date),
        sa.Column('probability', sa.Integer),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('client_id', sa.String(36), sa.ForeignKey('customers.id')),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date),
        sa.Column('budget', sa.Numeric(18, 2)),
        sa.Column('currency', sa.String(3), default='EGP'),
        sa.Column('manager_id', sa.String(36), sa.ForeignKey('employees.id')),
        sa.Column('status', sa.String(20), default='planning'),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_ar', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('assignee_id', sa.String(36), sa.ForeignKey('employees.id')),
        sa.Column('start_date', sa.Date),
        sa.Column('due_date', sa.Date),
        sa.Column('estimated_hours', sa.Numeric(8, 2)),
        sa.Column('actual_hours', sa.Numeric(8, 2)),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('status', sa.String(20), default='todo'),
        sa.Column('parent_task_id', sa.String(36), sa.ForeignKey('tasks.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_accounts_code', 'accounts', ['code'])
    op.create_index('ix_products_sku', 'products', ['sku'])
    op.create_index('ix_employees_employee_id', 'employees', ['employee_id'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_leads_email', 'leads', ['email'])
    op.create_index('ix_projects_client_id', 'projects', ['client_id'])
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('tasks')
    op.drop_table('projects')
    op.drop_table('opportunities')
    op.drop_table('leads')
    op.drop_table('customers')
    op.drop_table('positions')
    op.drop_table('departments')
    op.drop_table('employees')
    op.drop_table('stock_movements')
    op.drop_table('warehouses')
    op.drop_table('categories')
    op.drop_table('products')
    op.drop_table('journal_entry_lines')
    op.drop_table('journal_entries')
    op.drop_table('accounts')
    op.drop_table('industry_templates')
    op.drop_table('users')
    op.drop_table('tenants')
