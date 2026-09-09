"""
P40 Production Validation Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_validation_rules": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "rule_name": "VARCHAR(100) NOT NULL",
        "rule_type": "VARCHAR(50) NOT NULL",
        "check_command": "TEXT NOT NULL",
        "expected_value": "TEXT",
        "severity": "VARCHAR(20) DEFAULT 'error'",
        "is_active": "BOOLEAN DEFAULT true",
        "last_run_at": "TIMESTAMPTZ",
        "last_status": "VARCHAR(20)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_validation_results": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "rule_id": "VARCHAR(36)",
        "rule_name": "VARCHAR(100)",
        "check_type": "VARCHAR(50) NOT NULL",
        "status": "VARCHAR(20) NOT NULL",
        "actual_value": "TEXT",
        "expected_value": "TEXT",
        "message": "TEXT",
        "execution_time_ms": "INT",
        "validated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_health_checks": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "check_name": "VARCHAR(100) NOT NULL",
        "check_type": "VARCHAR(50) NOT NULL",
        "target": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "response_time_ms": "INT",
        "message": "TEXT",
        "last_run_at": "TIMESTAMPTZ",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_ssl_certificates": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "domain": "VARCHAR(255) NOT NULL",
        "issuer": "VARCHAR(255)",
        "serial_number": "VARCHAR(100)",
        "not_before": "TIMESTAMPTZ",
        "not_after": "TIMESTAMPTZ",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "auto_renew": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_environment_configs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "environment": "VARCHAR(30) NOT NULL",
        "config_key": "VARCHAR(100) NOT NULL",
        "config_value": "TEXT",
        "is_sensitive": "BOOLEAN DEFAULT false",
        "description": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_security_scans": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "scan_type": "VARCHAR(50) NOT NULL",
        "target": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "vulnerabilities_found": "INT DEFAULT 0",
        "critical_count": "INT DEFAULT 0",
        "high_count": "INT DEFAULT 0",
        "medium_count": "INT DEFAULT 0",
        "low_count": "INT DEFAULT 0",
        "report_url": "TEXT",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_validation_rules": ["tenant_id, rule_type", "is_active"],
    "dbp_validation_results": ["tenant_id, rule_id", "status, validated_at"],
    "dbp_health_checks": ["tenant_id, check_type", "status"],
    "dbp_ssl_certificates": ["tenant_id, domain", "not_after"],
    "dbp_environment_configs": ["tenant_id, environment", "config_key"],
    "dbp_security_scans": ["tenant_id, scan_type", "status, created_at"],
}

if __name__ == "__main__":
    print("Running P40 migration...")
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

    print("P40 migration complete.")
