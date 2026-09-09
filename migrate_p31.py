"""
P31 Migration — Audit & Compliance
  - dbp_audit_trail (enhanced from P6.3)
  - dbp_compliance_rules
  - dbp_data_access_logs
  - dbp_audit_exports
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_audit_trail": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "company_id": "VARCHAR(36)",
        "entity_type": "VARCHAR(100) NOT NULL",
        "entity_id": "VARCHAR(100)",
        "action": "VARCHAR(30) NOT NULL",
        "actor_id": "VARCHAR(100)",
        "actor_email": "VARCHAR(255)",
        "actor_roles": "TEXT",
        "old_values": "JSONB",
        "new_values": "JSONB",
        "ip_address": "VARCHAR(50)",
        "user_agent": "TEXT",
        "request_id": "VARCHAR(100)",
        "correlation_id": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_compliance_rules": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "company_id": "VARCHAR(36)",
        "rule_code": "VARCHAR(50) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "category": "VARCHAR(100)",
        "severity": "VARCHAR(20) DEFAULT 'medium'",
        "entity_type": "VARCHAR(100)",
        "rule_expression": "TEXT",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_data_access_logs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "user_id": "VARCHAR(100)",
        "user_email": "VARCHAR(255)",
        "action": "VARCHAR(30) NOT NULL",
        "resource_type": "VARCHAR(100)",
        "resource_id": "VARCHAR(100)",
        "access_granted": "BOOLEAN DEFAULT true",
        "denial_reason": "VARCHAR(255)",
        "ip_address": "VARCHAR(50)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_audit_exports": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "company_id": "VARCHAR(36)",
        "export_type": "VARCHAR(50) NOT NULL",
        "entity_types": "TEXT",
        "from_date": "DATE",
        "to_date": "DATE",
        "format": "VARCHAR(10) DEFAULT 'json'",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "record_count": "INT DEFAULT 0",
        "exported_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "completed_at": "TIMESTAMPTZ",
    },
}

INDEXES = {
    "dbp_audit_trail": ["tenant_id", "company_id", "entity_type", "entity_id", "action", "actor_id", "created_at"],
    "dbp_compliance_rules": ["tenant_id", "company_id", "category", "is_active"],
    "dbp_data_access_logs": ["tenant_id", "user_id", "resource_type", "action", "created_at"],
    "dbp_audit_exports": ["tenant_id", "company_id"],
}

if __name__ == "__main__":
    print("Running P31 migration...")
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
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})"))
                except Exception:
                    pass
    print("P31 migration complete.")
