"""Add HR module tables.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b3c4d5e6f7a8'
down_revision: str | Sequence[str] | None = 'a1b2c3d4e5f6'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('hr_departments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(50), nullable=False),
    sa.Column('name', sa.String(200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(30), nullable=False, server_default='active'),
    sa.Column('manager_id', sa.Uuid(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'inactive')", name='ck_hr_department_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'code', name='uq_hr_department_tenant_code')
    )
    op.create_index('ix_hr_department_tenant_status', 'hr_departments', ['tenant_id', 'status'], unique=False)

    op.create_table('hr_employees',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Uuid(), nullable=True),
    sa.Column('employee_number', sa.String(50), nullable=False),
    sa.Column('first_name', sa.String(100), nullable=False),
    sa.Column('last_name', sa.String(100), nullable=False),
    sa.Column('email', sa.String(200), nullable=False),
    sa.Column('phone', sa.String(50), nullable=True),
    sa.Column('hire_date', sa.Date(), nullable=False),
    sa.Column('job_title', sa.String(200), nullable=False),
    sa.Column('salary', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('status', sa.String(30), nullable=False, server_default='active'),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'inactive', 'terminated')", name='ck_hr_employee_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id'], ['hr_departments.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'employee_number', name='uq_hr_employee_tenant_number')
    )
    op.create_index('ix_hr_employee_tenant_status', 'hr_employees', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_hr_employee_tenant_department', 'hr_employees', ['tenant_id', 'department_id'], unique=False)

    op.create_table('hr_attendance',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('employee_id', sa.Uuid(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('check_in', sa.DateTime(timezone=True), nullable=True),
    sa.Column('check_out', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(30), nullable=False, server_default='present'),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('present', 'absent', 'late', 'leave')", name='ck_hr_attendance_status'),
    sa.ForeignKeyConstraint(['employee_id'], ['hr_employees.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'employee_id', 'date', name='uq_hr_attendance_tenant_emp_date')
    )
    op.create_index('ix_hr_attendance_tenant_employee', 'hr_attendance', ['tenant_id', 'employee_id'], unique=False)

    op.create_table('hr_leave_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('employee_id', sa.Uuid(), nullable=False),
    sa.Column('leave_type', sa.String(30), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('days', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='ck_hr_leave_request_status'),
    sa.CheckConstraint("leave_type IN ('annual', 'sick', 'personal', 'maternity', 'paternity', 'unpaid')", name='ck_hr_leave_request_type'),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['employee_id'], ['hr_employees.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'employee_id', 'start_date', name='uq_hr_leave_tenant_emp_start')
    )
    op.create_index('ix_hr_leave_request_tenant_employee', 'hr_leave_requests', ['tenant_id', 'employee_id'], unique=False)

    op.create_table('hr_payroll_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
    sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('processed_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'processed', 'paid')", name='ck_hr_payroll_run_status'),
    sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'period_start', name='uq_hr_payroll_tenant_period')
    )
    op.create_index('ix_hr_payroll_run_tenant_status', 'hr_payroll_runs', ['tenant_id', 'status'], unique=False)

    op.create_table('hr_payroll_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('payroll_run_id', sa.Uuid(), nullable=False),
    sa.Column('employee_id', sa.Uuid(), nullable=False),
    sa.Column('base_salary', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('deductions', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('net_pay', sa.Numeric(15, 2), nullable=False, server_default='0'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['hr_employees.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['payroll_run_id'], ['hr_payroll_runs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_hr_payroll_line_tenant_run', 'hr_payroll_lines', ['tenant_id', 'payroll_run_id'], unique=False)


def downgrade() -> None:
    op.drop_table('hr_payroll_lines')
    op.drop_table('hr_leave_requests')
    op.drop_table('hr_attendance')
    op.drop_table('hr_employees')
    op.drop_table('hr_payroll_runs')
    op.drop_table('hr_departments')
