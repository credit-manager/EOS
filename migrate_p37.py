"""
P37 System Integration & Health Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_system_config": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "config_key": "VARCHAR(100) NOT NULL",
        "config_value": "JSONB",
        "description": "TEXT",
        "category": "VARCHAR(50) DEFAULT 'general'",
        "is_sensitive": "BOOLEAN DEFAULT false",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_integration_logs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36)",
        "integration_type": "VARCHAR(50) NOT NULL",
        "direction": "VARCHAR(10) NOT NULL",
        "status": "VARCHAR(20) NOT NULL",
        "entity_type": "VARCHAR(100)",
        "entity_id": "VARCHAR(36)",
        "payload_summary": "TEXT",
        "error_message": "TEXT",
        "duration_ms": "INT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_data_imports": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "import_type": "VARCHAR(50) NOT NULL",
        "file_name": "VARCHAR(255)",
        "record_count": "INT DEFAULT 0",
        "success_count": "INT DEFAULT 0",
        "error_count": "INT DEFAULT 0",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "errors": "JSONB",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_data_exports": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "export_type": "VARCHAR(50) NOT NULL",
        "record_count": "INT DEFAULT 0",
        "file_format": "VARCHAR(10) DEFAULT 'csv'",
        "status": "VARCHAR(20) DEFAULT 'completed'",
        "download_url": "TEXT",
        "expires_at": "TIMESTAMPTZ",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_system_config": ["tenant_id, config_key"],
    "dbp_integration_logs": ["tenant_id, company_id", "created_at"],
    "dbp_data_imports": ["tenant_id, company_id"],
    "dbp_data_exports": ["tenant_id, company_id"],
}

if __name__ == "__main__":
    print("Running P37 migration...")
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
                    if table == "dbp_system_config" and col == "tenant_id, config_key":
                        conn.execute(text(
                            f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"
                        ))
                    else:
                        conn.execute(text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"
                        ))
                except Exception:
                    pass

    print("P37 migration complete.")
