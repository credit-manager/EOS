"""
P70.9.1 Services ERP Professional — Database Schema
=====================================================
25 services-specific tables + Commerce Engine + Core Platform integration.
Full lifecycle: CRM → Leads → Quotations → Projects → Timesheets → Invoicing → Profitability.
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from database import engine
from sqlalchemy import text

def uid():
    return str(uuid.uuid4())

TABLES = [
    # ─── CRM / Clients ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_clients (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        client_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        industry VARCHAR(100),
        website VARCHAR(300),
        phone VARCHAR(50),
        email VARCHAR(200),
        address TEXT,
        contact_person VARCHAR(200),
        credit_limit NUMERIC(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        source VARCHAR(50),
        notes TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Leads ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_leads (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        lead_number VARCHAR(50) NOT NULL,
        company_name VARCHAR(200) NOT NULL,
        contact_name VARCHAR(200),
        email VARCHAR(200),
        phone VARCHAR(50),
        source VARCHAR(50),
        status VARCHAR(20) DEFAULT 'new',
        priority INTEGER DEFAULT 5,
        estimated_value NUMERIC(15,2) DEFAULT 0,
        assigned_to VARCHAR(36),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Opportunities ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_opportunities (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        opp_number VARCHAR(50) NOT NULL,
        client_id VARCHAR(36),
        lead_id VARCHAR(36),
        name VARCHAR(200) NOT NULL,
        stage VARCHAR(30) DEFAULT 'qualification',
        probability NUMERIC(5,2) DEFAULT 50,
        expected_value NUMERIC(15,2) DEFAULT 0,
        close_date DATE,
        assigned_to VARCHAR(36),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Quotations ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_quotations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        quote_number VARCHAR(50) NOT NULL,
        client_id VARCHAR(36) NOT NULL,
        opportunity_id VARCHAR(36),
        title VARCHAR(200) NOT NULL,
        description TEXT,
        total NUMERIC(15,2) DEFAULT 0,
        tax NUMERIC(15,2) DEFAULT 0,
        discount NUMERIC(15,2) DEFAULT 0,
        grand_total NUMERIC(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'draft',
        valid_until DATE,
        notes TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_quote_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        quote_id VARCHAR(36) NOT NULL,
        description VARCHAR(500) NOT NULL,
        quantity NUMERIC(15,4) DEFAULT 1,
        unit_price NUMERIC(15,4) DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        total NUMERIC(15,2) DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Contracts ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_contracts (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        contract_number VARCHAR(50) NOT NULL,
        client_id VARCHAR(36) NOT NULL,
        title VARCHAR(200) NOT NULL,
        contract_type VARCHAR(30) DEFAULT 'fixed_price',
        value NUMERIC(15,2) DEFAULT 0,
        start_date DATE,
        end_date DATE,
        billing_cycle VARCHAR(20) DEFAULT 'monthly',
        auto_renew BOOLEAN DEFAULT FALSE,
        status VARCHAR(20) DEFAULT 'draft',
        notes TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Projects ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_projects (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        project_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        client_id VARCHAR(36),
        contract_id VARCHAR(36),
        project_type VARCHAR(30) DEFAULT 'time_material',
        budget NUMERIC(15,2) DEFAULT 0,
        spent NUMERIC(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'planning',
        priority INTEGER DEFAULT 5,
        start_date DATE,
        end_date DATE,
        manager_id VARCHAR(36),
        description TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Project Tasks ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_project_tasks (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        task_type VARCHAR(30) DEFAULT 'task',
        status VARCHAR(20) DEFAULT 'todo',
        priority INTEGER DEFAULT 5,
        assigned_to VARCHAR(36),
        estimated_hours NUMERIC(10,2) DEFAULT 0,
        actual_hours NUMERIC(10,2) DEFAULT 0,
        start_date DATE,
        due_date DATE,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Milestones ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_milestones (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        due_date DATE,
        amount NUMERIC(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Skills / Resources ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_skills (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        category VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_resource_allocations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        employee_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36) NOT NULL,
        allocation_pct NUMERIC(5,2) DEFAULT 100,
        start_date DATE,
        end_date DATE,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Timesheets ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_timesheets (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        timesheet_number VARCHAR(50) NOT NULL,
        employee_id VARCHAR(36) NOT NULL,
        week_start DATE NOT NULL,
        week_end DATE NOT NULL,
        total_hours NUMERIC(10,2) DEFAULT 0,
        billable_hours NUMERIC(10,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'draft',
        submitted_at TIMESTAMP WITH TIME ZONE,
        approved_by VARCHAR(36),
        approved_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_timesheet_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        timesheet_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36) NOT NULL,
        task_id VARCHAR(36),
        work_date DATE NOT NULL,
        hours NUMERIC(10,2) NOT NULL,
        billable BOOLEAN DEFAULT TRUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Expenses ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_expenses (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        expense_number VARCHAR(50) NOT NULL,
        employee_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36),
        category VARCHAR(50) NOT NULL,
        amount NUMERIC(15,2) NOT NULL,
        currency VARCHAR(10) DEFAULT 'SAR',
        expense_date DATE NOT NULL,
        description TEXT,
        receipt_ref VARCHAR(300),
        status VARCHAR(20) DEFAULT 'draft',
        approved_by VARCHAR(36),
        approved_at TIMESTAMP WITH TIME ZONE,
        invoiced BOOLEAN DEFAULT FALSE,
        invoice_id VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Service Invoices ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_invoices (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        invoice_number VARCHAR(50) NOT NULL,
        client_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36),
        contract_id VARCHAR(36),
        invoice_type VARCHAR(30) DEFAULT 'time_material',
        subtotal NUMERIC(15,2) DEFAULT 0,
        tax NUMERIC(15,2) DEFAULT 0,
        discount NUMERIC(15,2) DEFAULT 0,
        total NUMERIC(15,2) DEFAULT 0,
        paid_amount NUMERIC(15,2) DEFAULT 0,
        balance NUMERIC(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'draft',
        due_date DATE,
        paid_date DATE,
        journal_entry_id VARCHAR(36),
        notes TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_invoice_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        invoice_id VARCHAR(36) NOT NULL,
        description VARCHAR(500) NOT NULL,
        quantity NUMERIC(15,4) DEFAULT 1,
        unit_price NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,2) DEFAULT 0,
        timesheet_line_id VARCHAR(36),
        expense_id VARCHAR(36),
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Profitability ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_svc_profitability (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        project_id VARCHAR(36) NOT NULL,
        revenue NUMERIC(15,2) DEFAULT 0,
        labor_cost NUMERIC(15,2) DEFAULT 0,
        expense_cost NUMERIC(15,2) DEFAULT 0,
        overhead NUMERIC(15,2) DEFAULT 0,
        profit NUMERIC(15,2) DEFAULT 0,
        margin_pct NUMERIC(5,2) DEFAULT 0,
        calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

# ─── Indexes ─────────────────────────────────────────
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_svc_client_tenant ON dbp_svc_clients(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_client_code ON dbp_svc_clients(tenant_id, client_code)",
    "CREATE INDEX IF NOT EXISTS idx_svc_lead_tenant ON dbp_svc_leads(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_lead_status ON dbp_svc_leads(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_svc_opp_tenant ON dbp_svc_opportunities(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_opp_stage ON dbp_svc_opportunities(tenant_id, stage)",
    "CREATE INDEX IF NOT EXISTS idx_svc_quote_tenant ON dbp_svc_quotations(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_quote_client ON dbp_svc_quotations(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_quote_lines ON dbp_svc_quote_lines(quote_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_contract_tenant ON dbp_svc_contracts(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_contract_client ON dbp_svc_contracts(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_project_tenant ON dbp_svc_projects(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_project_client ON dbp_svc_projects(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_project_status ON dbp_svc_projects(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_svc_task_tenant ON dbp_svc_project_tasks(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_task_project ON dbp_svc_project_tasks(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_task_status ON dbp_svc_project_tasks(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_svc_milestone_project ON dbp_svc_milestones(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_alloc_tenant ON dbp_svc_resource_allocations(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_alloc_project ON dbp_svc_resource_allocations(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_ts_tenant ON dbp_svc_timesheets(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_ts_employee ON dbp_svc_timesheets(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_ts_status ON dbp_svc_timesheets(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_svc_ts_lines ON dbp_svc_timesheet_lines(timesheet_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_ts_lines_project ON dbp_svc_timesheet_lines(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_exp_tenant ON dbp_svc_expenses(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_exp_employee ON dbp_svc_expenses(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_exp_project ON dbp_svc_expenses(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_inv_tenant ON dbp_svc_invoices(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_inv_client ON dbp_svc_invoices(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_inv_project ON dbp_svc_invoices(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_inv_status ON dbp_svc_invoices(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_svc_inv_lines ON dbp_svc_invoice_lines(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_svc_profit_project ON dbp_svc_profitability(project_id)",
]

# ─── Unique Constraints ──────────────────────────────
UNIQUES = [
    "ALTER TABLE dbp_svc_clients ADD CONSTRAINT uq_svc_client_code UNIQUE (tenant_id, client_code)",
    "ALTER TABLE dbp_svc_leads ADD CONSTRAINT uq_svc_lead_number UNIQUE (tenant_id, lead_number)",
    "ALTER TABLE dbp_svc_opportunities ADD CONSTRAINT uq_svc_opp_number UNIQUE (tenant_id, opp_number)",
    "ALTER TABLE dbp_svc_quotations ADD CONSTRAINT uq_svc_quote_number UNIQUE (tenant_id, quote_number)",
    "ALTER TABLE dbp_svc_contracts ADD CONSTRAINT uq_svc_contract_number UNIQUE (tenant_id, contract_number)",
    "ALTER TABLE dbp_svc_projects ADD CONSTRAINT uq_svc_project_code UNIQUE (tenant_id, project_code)",
    "ALTER TABLE dbp_svc_timesheets ADD CONSTRAINT uq_svc_ts_number UNIQUE (tenant_id, timesheet_number)",
    "ALTER TABLE dbp_svc_expenses ADD CONSTRAINT uq_svc_exp_number UNIQUE (tenant_id, expense_number)",
    "ALTER TABLE dbp_svc_invoices ADD CONSTRAINT uq_svc_inv_number UNIQUE (tenant_id, invoice_number)",
]

# ─── CHECK Constraints ───────────────────────────────
CHECKS = [
    "ALTER TABLE dbp_svc_clients ADD CONSTRAINT chk_svc_client_status CHECK (status IN ('active','inactive','archived'))",
    "ALTER TABLE dbp_svc_leads ADD CONSTRAINT chk_svc_lead_status CHECK (status IN ('new','contacted','qualified','unqualified','converted','lost'))",
    "ALTER TABLE dbp_svc_leads ADD CONSTRAINT chk_svc_lead_priority CHECK (priority >= 1 AND priority <= 10)",
    "ALTER TABLE dbp_svc_opportunities ADD CONSTRAINT chk_svc_opp_stage CHECK (stage IN ('qualification','proposal','negotiation','closed_won','closed_lost'))",
    "ALTER TABLE dbp_svc_opportunities ADD CONSTRAINT chk_svc_opp_probability CHECK (probability >= 0 AND probability <= 100)",
    "ALTER TABLE dbp_svc_quotations ADD CONSTRAINT chk_svc_quote_status CHECK (status IN ('draft','sent','accepted','rejected','expired'))",
    "ALTER TABLE dbp_svc_quote_lines ADD CONSTRAINT chk_svc_ql_qty CHECK (quantity > 0)",
    "ALTER TABLE dbp_svc_quote_lines ADD CONSTRAINT chk_svc_ql_price CHECK (unit_price >= 0)",
    "ALTER TABLE dbp_svc_contracts ADD CONSTRAINT chk_svc_contract_type CHECK (contract_type IN ('fixed_price','time_material','retainer','milestone'))",
    "ALTER TABLE dbp_svc_contracts ADD CONSTRAINT chk_svc_contract_status CHECK (status IN ('draft','active','completed','terminated'))",
    "ALTER TABLE dbp_svc_projects ADD CONSTRAINT chk_svc_proj_type CHECK (project_type IN ('time_material','fixed_price','retainer'))",
    "ALTER TABLE dbp_svc_projects ADD CONSTRAINT chk_svc_proj_status CHECK (status IN ('planning','active','on_hold','completed','cancelled'))",
    "ALTER TABLE dbp_svc_projects ADD CONSTRAINT chk_svc_proj_budget CHECK (budget >= 0)",
    "ALTER TABLE dbp_svc_project_tasks ADD CONSTRAINT chk_svc_task_status CHECK (status IN ('todo','in_progress','review','done','blocked'))",
    "ALTER TABLE dbp_svc_project_tasks ADD CONSTRAINT chk_svc_task_hours CHECK (estimated_hours >= 0 AND actual_hours >= 0)",
    "ALTER TABLE dbp_svc_milestones ADD CONSTRAINT chk_svc_milestone_status CHECK (status IN ('pending','completed','overdue'))",
    "ALTER TABLE dbp_svc_timesheets ADD CONSTRAINT chk_svc_ts_status CHECK (status IN ('draft','submitted','approved','rejected'))",
    "ALTER TABLE dbp_svc_timesheet_lines ADD CONSTRAINT chk_svc_tsl_hours CHECK (hours > 0)",
    "ALTER TABLE dbp_svc_expenses ADD CONSTRAINT chk_svc_exp_category CHECK (category IN ('travel','meals','office','software','hardware','other'))",
    "ALTER TABLE dbp_svc_expenses ADD CONSTRAINT chk_svc_exp_status CHECK (status IN ('draft','submitted','approved','rejected'))",
    "ALTER TABLE dbp_svc_expenses ADD CONSTRAINT chk_svc_exp_amount CHECK (amount > 0)",
    "ALTER TABLE dbp_svc_invoices ADD CONSTRAINT chk_svc_inv_type CHECK (invoice_type IN ('time_material','fixed_price','milestone','retainer','expense'))",
    "ALTER TABLE dbp_svc_invoices ADD CONSTRAINT chk_svc_inv_status CHECK (status IN ('draft','sent','paid','overdue','cancelled'))",
    "ALTER TABLE dbp_svc_invoices ADD CONSTRAINT chk_svc_inv_total CHECK (total >= 0)",
    "ALTER TABLE dbp_svc_profitability ADD CONSTRAINT chk_svc_profit_margin CHECK (margin_pct >= -100 AND margin_pct <= 1000)",
]

# ─── Defaults ────────────────────────────────────────
DEFAULTS = [
    "ALTER TABLE dbp_svc_clients ALTER COLUMN status SET DEFAULT 'active'",
    "ALTER TABLE dbp_svc_clients ALTER COLUMN credit_limit SET DEFAULT 0",
    "ALTER TABLE dbp_svc_leads ALTER COLUMN status SET DEFAULT 'new'",
    "ALTER TABLE dbp_svc_leads ALTER COLUMN priority SET DEFAULT 5",
    "ALTER TABLE dbp_svc_leads ALTER COLUMN estimated_value SET DEFAULT 0",
    "ALTER TABLE dbp_svc_opportunities ALTER COLUMN stage SET DEFAULT 'qualification'",
    "ALTER TABLE dbp_svc_opportunities ALTER COLUMN probability SET DEFAULT 50",
    "ALTER TABLE dbp_svc_quotations ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_svc_contracts ALTER COLUMN contract_type SET DEFAULT 'fixed_price'",
    "ALTER TABLE dbp_svc_contracts ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_svc_contracts ALTER COLUMN billing_cycle SET DEFAULT 'monthly'",
    "ALTER TABLE dbp_svc_projects ALTER COLUMN project_type SET DEFAULT 'time_material'",
    "ALTER TABLE dbp_svc_projects ALTER COLUMN status SET DEFAULT 'planning'",
    "ALTER TABLE dbp_svc_projects ALTER COLUMN priority SET DEFAULT 5",
    "ALTER TABLE dbp_svc_project_tasks ALTER COLUMN status SET DEFAULT 'todo'",
    "ALTER TABLE dbp_svc_project_tasks ALTER COLUMN priority SET DEFAULT 5",
    "ALTER TABLE dbp_svc_timesheets ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_svc_timesheet_lines ALTER COLUMN billable SET DEFAULT TRUE",
    "ALTER TABLE dbp_svc_expenses ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_svc_expenses ALTER COLUMN currency SET DEFAULT 'SAR'",
    "ALTER TABLE dbp_svc_expenses ALTER COLUMN invoiced SET DEFAULT FALSE",
    "ALTER TABLE dbp_svc_invoices ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_svc_invoices ALTER COLUMN paid_amount SET DEFAULT 0",
]


def migrate():
    created = 0
    idx_created = 0
    uq_created = 0
    chk_created = 0
    df_created = 0
    with engine.begin() as conn:
        for sql in TABLES:
            try:
                conn.execute(text(sql.strip()))
                created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  WARN table: {e}")
        for sql in INDEXES:
            try:
                conn.execute(text(sql))
                idx_created += 1
            except Exception:
                pass
        for sql in UNIQUES:
            try:
                conn.execute(text(sql))
                uq_created += 1
            except Exception:
                pass
        for sql in CHECKS:
            try:
                conn.execute(text(sql))
                chk_created += 1
            except Exception:
                pass
        for sql in DEFAULTS:
            try:
                conn.execute(text(sql))
                df_created += 1
            except Exception:
                pass

    print(f"P70.9.1 Services Schema:")
    print(f"  Tables:     {created}/{len(TABLES)}")
    print(f"  Indexes:    {idx_created}/{len(INDEXES)}")
    print(f"  Uniques:    {uq_created}/{len(UNIQUES)}")
    print(f"  Checks:     {chk_created}/{len(CHECKS)}")
    print(f"  Defaults:   {df_created}/{len(DEFAULTS)}")
    print("  DONE")


if __name__ == "__main__":
    migrate()
