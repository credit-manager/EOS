"""
P41 SaaS Control Plane Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_saas_tenants": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(200) NOT NULL",
        "slug": "VARCHAR(100) NOT NULL",
        "status": "VARCHAR(30) DEFAULT 'active'",
        "plan_id": "VARCHAR(36)",
        "max_users": "INT DEFAULT 10",
        "max_companies": "INT DEFAULT 1",
        "settings": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_saas_plans": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "plan_name": "VARCHAR(100) NOT NULL",
        "plan_code": "VARCHAR(50) NOT NULL",
        "price_monthly": "DOUBLE PRECISION DEFAULT 0",
        "price_yearly": "DOUBLE PRECISION DEFAULT 0",
        "max_users": "INT DEFAULT 10",
        "max_companies": "INT DEFAULT 1",
        "max_storage_gb": "INT DEFAULT 5",
        "features": "JSONB",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_saas_features": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "feature_name": "VARCHAR(100) NOT NULL",
        "feature_code": "VARCHAR(50) NOT NULL",
        "description": "TEXT",
        "category": "VARCHAR(50)",
        "is_default": "BOOLEAN DEFAULT false",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_saas_tenant_features": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "feature_id": "VARCHAR(36) NOT NULL",
        "is_enabled": "BOOLEAN DEFAULT true",
        "config": "JSONB",
        "enabled_at": "TIMESTAMPTZ DEFAULT NOW()",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_saas_usage": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "usage_type": "VARCHAR(50) NOT NULL",
        "usage_value": "DOUBLE PRECISION DEFAULT 0",
        "period_start": "TIMESTAMPTZ",
        "period_end": "TIMESTAMPTZ",
        "recorded_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_saas_tenants": ["tenant_id, status", "slug"],
    "dbp_saas_plans": ["tenant_id, plan_code", "is_active"],
    "dbp_saas_features": ["feature_code"],
    "dbp_saas_tenant_features": ["tenant_id, feature_id"],
    "dbp_saas_usage": ["tenant_id, usage_type", "period_start"],
}

if __name__ == "__main__":
    print("Running P41 migration...")
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
                    unique = "UNIQUE " if table == "dbp_saas_tenants" and "slug" in col else ""
                    conn.execute(text(
                        f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} ON {table}({col})"
                    ))
                except Exception:
                    pass

    print("P41 migration complete.")
