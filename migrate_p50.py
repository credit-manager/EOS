"""
P50 Platform Maturity & Certification Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_certification_scores": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "certification_level": "VARCHAR(50) NOT NULL",
        "total_score": "INT NOT NULL",
        "max_score": "INT NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "assessed_at": "TIMESTAMPTZ",
        "expires_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_maturity_metrics": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "metric_category": "VARCHAR(50) NOT NULL",
        "metric_name": "VARCHAR(100) NOT NULL",
        "metric_value": "DOUBLE PRECISION NOT NULL",
        "target_value": "DOUBLE PRECISION",
        "status": "VARCHAR(20) DEFAULT 'measured'",
        "measured_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_platform_features": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "feature_name": "VARCHAR(200) NOT NULL",
        "feature_category": "VARCHAR(50) NOT NULL",
        "version_added": "VARCHAR(20) NOT NULL",
        "is_stable": "BOOLEAN DEFAULT false",
        "deprecated_at": "TIMESTAMPTZ",
        "metadata": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_upgrade_history": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "from_version": "VARCHAR(20) NOT NULL",
        "to_version": "VARCHAR(20) NOT NULL",
        "upgrade_type": "VARCHAR(20) NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'completed'",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ DEFAULT NOW()",
        "notes": "TEXT",
    },
    "dbp_platform_health": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "component_name": "VARCHAR(100) NOT NULL",
        "health_score": "DOUBLE PRECISION NOT NULL",
        "status": "VARCHAR(20) NOT NULL",
        "details": "JSONB",
        "checked_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_certification_scores": ["tenant_id, status"],
    "dbp_maturity_metrics": ["tenant_id, metric_category"],
    "dbp_platform_features": ["feature_category, is_stable"],
    "dbp_upgrade_history": ["tenant_id, to_version"],
    "dbp_platform_health": ["tenant_id, component_name"],
}

if __name__ == "__main__":
    print("Running P50 migration...")
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

    print("P50 migration complete.")
