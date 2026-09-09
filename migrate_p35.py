"""
P35 Business Intelligence & Reporting Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_report_templates": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "report_type": "VARCHAR(50) NOT NULL",
        "data_source": "VARCHAR(100) NOT NULL",
        "parameters": "JSONB",
        "columns": "JSONB",
        "filters": "JSONB",
        "sort_config": "JSONB",
        "is_public": "BOOLEAN DEFAULT false",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_report_runs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "template_id": "VARCHAR(36)",
        "report_name": "VARCHAR(255)",
        "parameters": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "result_count": "INT DEFAULT 0",
        "result_data": "JSONB",
        "format": "VARCHAR(10) DEFAULT 'json'",
        "error_message": "TEXT",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_scheduled_reports": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "template_id": "VARCHAR(36)",
        "name": "VARCHAR(255) NOT NULL",
        "schedule_cron": "VARCHAR(100)",
        "recipients": "TEXT",
        "format": "VARCHAR(10) DEFAULT 'csv'",
        "is_active": "BOOLEAN DEFAULT true",
        "last_run": "TIMESTAMPTZ",
        "next_run": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_report_templates": ["tenant_id, company_id"],
    "dbp_report_runs": ["tenant_id, company_id", "template_id"],
    "dbp_scheduled_reports": ["tenant_id, company_id", "template_id"],
}

if __name__ == "__main__":
    print("Running P35 migration...")
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
                col_clean = col.replace(", ", "_")
                idx_name = f"idx_{table}_{col_clean}"
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"))
                except Exception:
                    pass

    print("P35 migration complete.")
