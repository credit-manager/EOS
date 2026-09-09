"""
P39 Production Deployment & Operations Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_backup_jobs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36)",
        "backup_type": "VARCHAR(50) NOT NULL",
        "target_tables": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "file_path": "TEXT",
        "file_size_bytes": "BIGINT",
        "checksum": "VARCHAR(64)",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "error_message": "TEXT",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_scheduled_jobs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "job_name": "VARCHAR(100) NOT NULL",
        "job_type": "VARCHAR(50) NOT NULL",
        "cron_expression": "VARCHAR(50)",
        "interval_seconds": "INT",
        "payload": "JSONB",
        "is_active": "BOOLEAN DEFAULT true",
        "last_run_at": "TIMESTAMPTZ",
        "next_run_at": "TIMESTAMPTZ",
        "run_count": "INT DEFAULT 0",
        "last_status": "VARCHAR(20)",
        "last_error": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_alert_rules": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36)",
        "rule_name": "VARCHAR(100) NOT NULL",
        "metric_name": "VARCHAR(100) NOT NULL",
        "condition_op": "VARCHAR(10) NOT NULL",
        "threshold_value": "DOUBLE PRECISION NOT NULL",
        "severity": "VARCHAR(20) DEFAULT 'warning'",
        "notification_channels": "JSONB",
        "is_active": "BOOLEAN DEFAULT true",
        "cooldown_minutes": "INT DEFAULT 5",
        "last_triggered_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_alert_history": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "rule_id": "VARCHAR(36) NOT NULL",
        "rule_name": "VARCHAR(100)",
        "metric_name": "VARCHAR(100)",
        "actual_value": "DOUBLE PRECISION",
        "threshold_value": "DOUBLE PRECISION",
        "severity": "VARCHAR(20)",
        "status": "VARCHAR(20) DEFAULT 'firing'",
        "message": "TEXT",
        "acknowledged_by": "VARCHAR(100)",
        "acknowledged_at": "TIMESTAMPTZ",
        "resolved_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_deployments": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "version": "VARCHAR(50) NOT NULL",
        "environment": "VARCHAR(30) NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "deployed_by": "VARCHAR(100)",
        "commit_sha": "VARCHAR(40)",
        "release_notes": "TEXT",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "rolled_back_at": "TIMESTAMPTZ",
        "rollback_reason": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_monitoring_metrics": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "metric_name": "VARCHAR(100) NOT NULL",
        "metric_value": "DOUBLE PRECISION NOT NULL",
        "unit": "VARCHAR(20)",
        "tags": "JSONB",
        "source": "VARCHAR(50)",
        "recorded_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_backup_jobs": ["tenant_id, company_id", "status, created_at"],
    "dbp_scheduled_jobs": ["tenant_id, is_active", "next_run_at"],
    "dbp_alert_rules": ["tenant_id, company_id", "is_active"],
    "dbp_alert_history": ["tenant_id, rule_id", "status, created_at"],
    "dbp_deployments": ["tenant_id, environment", "created_at"],
    "dbp_monitoring_metrics": ["tenant_id, metric_name", "recorded_at"],
}

if __name__ == "__main__":
    print("Running P39 migration...")
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
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"
                    ))
                except Exception:
                    pass

    print("P39 migration complete.")
