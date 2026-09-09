"""
P48 IoT & Device Management Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_iot_devices": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "device_name": "VARCHAR(200) NOT NULL",
        "device_type": "VARCHAR(50) NOT NULL",
        "device_model": "VARCHAR(100)",
        "serial_number": "VARCHAR(100)",
        "firmware_version": "VARCHAR(50)",
        "status": "VARCHAR(20) DEFAULT 'online'",
        "location": "VARCHAR(200)",
        "metadata": "JSONB",
        "last_heartbeat_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_iot_telemetry": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "device_id": "VARCHAR(36) NOT NULL",
        "metric_name": "VARCHAR(100) NOT NULL",
        "metric_value": "DOUBLE PRECISION NOT NULL",
        "unit": "VARCHAR(20)",
        "quality_score": "DOUBLE PRECISION DEFAULT 1.0",
        "recorded_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_iot_alerts": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "device_id": "VARCHAR(36) NOT NULL",
        "alert_type": "VARCHAR(50) NOT NULL",
        "severity": "VARCHAR(20) NOT NULL",
        "message": "TEXT",
        "is_acknowledged": "BOOLEAN DEFAULT false",
        "acknowledged_by": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "acknowledged_at": "TIMESTAMPTZ",
    },
    "dbp_iot_rules": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "rule_name": "VARCHAR(200) NOT NULL",
        "device_type": "VARCHAR(50)",
        "condition_config": "JSONB NOT NULL",
        "action_config": "JSONB NOT NULL",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_iot_firmware": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "device_type": "VARCHAR(50) NOT NULL",
        "version": "VARCHAR(50) NOT NULL",
        "changelog": "TEXT",
        "download_url": "TEXT",
        "file_size_bytes": "BIGINT",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_iot_devices": ["tenant_id, device_type", "tenant_id, status"],
    "dbp_iot_telemetry": ["device_id, metric_name, recorded_at", "tenant_id, recorded_at"],
    "dbp_iot_alerts": ["device_id, is_acknowledged", "tenant_id, severity"],
    "dbp_iot_rules": ["tenant_id, device_type, is_active"],
    "dbp_iot_firmware": ["tenant_id, device_type"],
}

if __name__ == "__main__":
    print("Running P48 migration...")
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

    print("P48 migration complete.")
