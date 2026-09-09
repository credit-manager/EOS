"""
P28 Migration — Project Management
  - dbp_projects
  - dbp_project_tasks
  - dbp_project_milestones
  - dbp_project_time_entries
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_projects": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50)",
        "name": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "start_date": "DATE",
        "end_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'planning'",
        "budget": "NUMERIC(18,4) DEFAULT 0",
        "actual_cost": "NUMERIC(18,4) DEFAULT 0",
        "manager_id": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_project_tasks": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "project_id": "VARCHAR(36) NOT NULL",
        "parent_task_id": "VARCHAR(36)",
        "name": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "assigned_to": "VARCHAR(100)",
        "status": "VARCHAR(20) DEFAULT 'todo'",
        "priority": "VARCHAR(20) DEFAULT 'normal'",
        "start_date": "DATE",
        "due_date": "DATE",
        "estimated_hours": "NUMERIC(8,2)",
        "actual_hours": "NUMERIC(8,2) DEFAULT 0",
        "sort_order": "INT DEFAULT 0",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_project_milestones": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "project_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "due_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "completed_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_project_time_entries": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "project_id": "VARCHAR(36) NOT NULL",
        "task_id": "VARCHAR(36)",
        "employee_id": "VARCHAR(100)",
        "work_date": "DATE",
        "hours": "NUMERIC(6,2) NOT NULL",
        "notes": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_projects": ["tenant_id", "company_id"],
    "dbp_project_tasks": ["tenant_id", "project_id"],
    "dbp_project_milestones": ["tenant_id", "project_id"],
    "dbp_project_time_entries": ["tenant_id", "project_id"],
}

if __name__ == "__main__":
    print("Running P28 migration...")
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
    print("P28 migration complete.")
