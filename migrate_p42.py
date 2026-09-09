"""
P42 Tenant Lifecycle Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_tenant_lifecycle_events": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "event_type": "VARCHAR(50) NOT NULL",
        "event_data": "JSONB",
        "actor_id": "VARCHAR(100)",
        "actor_email": "VARCHAR(200)",
        "reason": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_tenant_data_exports": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "export_type": "VARCHAR(50) NOT NULL",
        "entity_types": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "file_path": "TEXT",
        "file_size_bytes": "BIGINT",
        "record_count": "INT DEFAULT 0",
        "requested_by": "VARCHAR(100)",
        "started_at": "TIMESTAMPTZ",
        "completed_at": "TIMESTAMPTZ",
        "expires_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_tenant_invitations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "email": "VARCHAR(200) NOT NULL",
        "role": "VARCHAR(50) NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "invited_by": "VARCHAR(100)",
        "accepted_at": "TIMESTAMPTZ",
        "expires_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_tenant_activity_logs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "user_id": "VARCHAR(100)",
        "action": "VARCHAR(100) NOT NULL",
        "resource_type": "VARCHAR(100)",
        "resource_id": "VARCHAR(36)",
        "details": "JSONB",
        "ip_address": "VARCHAR(45)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_tenant_notifications": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "notification_type": "VARCHAR(50) NOT NULL",
        "title": "VARCHAR(200) NOT NULL",
        "message": "TEXT",
        "severity": "VARCHAR(20) DEFAULT 'info'",
        "is_read": "BOOLEAN DEFAULT false",
        "action_url": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_tenant_lifecycle_events": ["tenant_id, event_type", "created_at"],
    "dbp_tenant_data_exports": ["tenant_id, status", "created_at"],
    "dbp_tenant_invitations": ["tenant_id, email", "status"],
    "dbp_tenant_activity_logs": ["tenant_id, action", "created_at"],
    "dbp_tenant_notifications": ["tenant_id, is_read", "created_at"],
}

if __name__ == "__main__":
    print("Running P42 migration...")
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

    print("P42 migration complete.")
