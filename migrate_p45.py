"""
P45 Advanced Analytics & Data Pipeline Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_analytics_dashboards": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "dashboard_name": "VARCHAR(200) NOT NULL",
        "dashboard_type": "VARCHAR(50) NOT NULL",
        "layout_config": "JSONB",
        "is_shared": "BOOLEAN DEFAULT false",
        "owner_id": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_analytics_widgets": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "dashboard_id": "VARCHAR(36) NOT NULL",
        "widget_type": "VARCHAR(50) NOT NULL",
        "title": "VARCHAR(200)",
        "config": "JSONB",
        "position_x": "INT DEFAULT 0",
        "position_y": "INT DEFAULT 0",
        "width": "INT DEFAULT 6",
        "height": "INT DEFAULT 4",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_data_pipelines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "pipeline_name": "VARCHAR(200) NOT NULL",
        "source_type": "VARCHAR(50) NOT NULL",
        "target_type": "VARCHAR(50) NOT NULL",
        "config": "JSONB",
        "schedule": "VARCHAR(100)",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "last_run_at": "TIMESTAMPTZ",
        "next_run_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_pipeline_runs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "pipeline_id": "VARCHAR(36) NOT NULL",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'running'",
        "records_processed": "INT DEFAULT 0",
        "records_failed": "INT DEFAULT 0",
        "error_message": "TEXT",
        "started_at": "TIMESTAMPTZ DEFAULT NOW()",
        "completed_at": "TIMESTAMPTZ",
    },
    "dbp_analytics_alerts": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "alert_name": "VARCHAR(200) NOT NULL",
        "metric_name": "VARCHAR(100) NOT NULL",
        "condition": "VARCHAR(30) NOT NULL",
        "threshold_value": "DOUBLE PRECISION NOT NULL",
        "notification_channels": "JSONB",
        "is_active": "BOOLEAN DEFAULT true",
        "last_triggered_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_analytics_dashboards": ["tenant_id, dashboard_type"],
    "dbp_analytics_widgets": ["dashboard_id"],
    "dbp_data_pipelines": ["tenant_id, status"],
    "dbp_pipeline_runs": ["pipeline_id, status", "tenant_id, started_at"],
    "dbp_analytics_alerts": ["tenant_id, is_active"],
}

if __name__ == "__main__":
    print("Running P45 migration...")
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

    print("P45 migration complete.")
