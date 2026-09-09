"""
P34 Migration - API Rate Limiting & Quotas
  - dbp_api_keys
  - dbp_api_usage_logs
  - dbp_rate_limit_rules
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_api_keys": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36)",
        "key_hash": "VARCHAR(255) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "permissions": "TEXT",
        "rate_limit_read": "INT DEFAULT 200",
        "rate_limit_write": "INT DEFAULT 50",
        "is_active": "BOOLEAN DEFAULT true",
        "expires_at": "TIMESTAMPTZ",
        "last_used_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_api_usage_logs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "api_key_id": "VARCHAR(36)",
        "endpoint": "VARCHAR(255)",
        "method": "VARCHAR(10)",
        "status_code": "INT",
        "response_time_ms": "INT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_rate_limit_rules": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "company_id": "VARCHAR(36)",
        "endpoint_pattern": "VARCHAR(255)",
        "method": "VARCHAR(10)",
        "rate_limit": "INT DEFAULT 60",
        "burst_limit": "INT DEFAULT 10",
        "window_seconds": "INT DEFAULT 60",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_api_keys": ["tenant_id"],
    "dbp_api_usage_logs": ["api_key_id, created_at"],
    "dbp_rate_limit_rules": ["tenant_id, endpoint_pattern"],
}

if __name__ == "__main__":
    print("Running P34 migration...")
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

    print("P34 migration complete.")
