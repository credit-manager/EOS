"""
P27 Migration — Human Resources (HR)
  - dbp_employees
  - dbp_leave_requests
  - dbp_attendance
  - dbp_payroll_runs
  - dbp_payroll_lines
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_employees": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "employee_code": "VARCHAR(50) NOT NULL",
        "first_name": "VARCHAR(100) NOT NULL",
        "last_name": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(255)",
        "phone": "VARCHAR(50)",
        "department_id": "VARCHAR(36)",
        "position": "VARCHAR(100)",
        "hire_date": "DATE NOT NULL",
        "termination_date": "DATE",
        "employment_status": "VARCHAR(20) DEFAULT 'active'",
        "salary": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "manager_id": "VARCHAR(36)",
        "cost_center_id": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_leave_requests": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "employee_id": "VARCHAR(36) NOT NULL",
        "leave_type": "VARCHAR(30) NOT NULL",
        "start_date": "DATE NOT NULL",
        "end_date": "DATE NOT NULL",
        "days": "INT NOT NULL",
        "reason": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "approved_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_attendance": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "employee_id": "VARCHAR(36) NOT NULL",
        "work_date": "DATE NOT NULL",
        "clock_in": "TIMESTAMPTZ",
        "clock_out": "TIMESTAMPTZ",
        "hours_worked": "NUMERIC(6,2) DEFAULT 0",
        "overtime_hours": "NUMERIC(6,2) DEFAULT 0",
        "status": "VARCHAR(20) DEFAULT 'present'",
        "notes": "TEXT",
    },
    "dbp_payroll_runs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "run_number": "VARCHAR(50) NOT NULL",
        "pay_period_start": "DATE NOT NULL",
        "pay_period_end": "DATE NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_gross": "NUMERIC(18,4) DEFAULT 0",
        "total_deductions": "NUMERIC(18,4) DEFAULT 0",
        "total_net": "NUMERIC(18,4) DEFAULT 0",
        "processed_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_payroll_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "run_id": "VARCHAR(36) REFERENCES dbp_payroll_runs(id) ON DELETE CASCADE",
        "employee_id": "VARCHAR(36) NOT NULL",
        "basic_salary": "NUMERIC(18,4) DEFAULT 0",
        "allowances": "NUMERIC(18,4) DEFAULT 0",
        "bonus": "NUMERIC(18,4) DEFAULT 0",
        "deductions": "NUMERIC(18,4) DEFAULT 0",
        "tax": "NUMERIC(18,4) DEFAULT 0",
        "net_pay": "NUMERIC(18,4) DEFAULT 0",
    },
}

INDEXES = {
    "dbp_employees": ["tenant_id", "company_id", "employee_code", "department_id"],
    "dbp_leave_requests": ["tenant_id", "employee_id", "status"],
    "dbp_attendance": ["tenant_id", "employee_id", "work_date"],
    "dbp_payroll_runs": ["tenant_id", "company_id"],
    "dbp_payroll_lines": ["run_id", "employee_id"],
}

if __name__ == "__main__":
    print("Running P27 migration...")
    with engine.begin() as conn:
        for table, cols in TABLES.items():
            exists = conn.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{table}')"
            )).scalar()
            if not exists:
                col_defs = ", ".join(f"{c} {t}" for c, t in cols.items())
                conn.execute(text(f"CREATE TABLE {table} ({col_defs})"))
                print(f"  [OK] {table}")
            else:
                existing = {r[0] for r in conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
                )).fetchall()}
                for col, typ in cols.items():
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
                        print(f"  [OK] Added {col} to {table}")
        for table, cols in INDEXES.items():
            for col in cols:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})"))
                except Exception:
                    pass
    print("P27 migration complete.")
