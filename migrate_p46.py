"""
P46 Compliance Automation & Policy Engine Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_compliance_policies": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "policy_name": "VARCHAR(200) NOT NULL",
        "policy_type": "VARCHAR(50) NOT NULL",
        "description": "TEXT",
        "rules_config": "JSONB NOT NULL",
        "severity": "VARCHAR(20) DEFAULT 'medium'",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_compliance_checks": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "policy_id": "VARCHAR(36) NOT NULL",
        "check_name": "VARCHAR(200) NOT NULL",
        "check_type": "VARCHAR(50) NOT NULL",
        "target_entity": "VARCHAR(100)",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "result_detail": "JSONB",
        "ran_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_compliance_violations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "policy_id": "VARCHAR(36) NOT NULL",
        "check_id": "VARCHAR(36)",
        "entity_type": "VARCHAR(100)",
        "entity_id": "VARCHAR(36)",
        "violation_type": "VARCHAR(100) NOT NULL",
        "severity": "VARCHAR(20) NOT NULL",
        "description": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'open",
        "assigned_to": "VARCHAR(36)",
        "resolved_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_compliance_audit_log": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "action": "VARCHAR(50) NOT NULL",
        "entity_type": "VARCHAR(100)",
        "entity_id": "VARCHAR(36)",
        "actor_id": "VARCHAR(36)",
        "details": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_compliance_frameworks": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "framework_name": "VARCHAR(100) NOT NULL",
        "framework_type": "VARCHAR(50) NOT NULL",
        "version": "VARCHAR(20)",
        "requirements": "JSONB",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

# Fix: status column has unclosed quote in TABLES above - corrected below
TABLES["dbp_compliance_violations"]["status"] = "VARCHAR(20) DEFAULT 'open'"

INDEXES = {
    "dbp_compliance_policies": ["tenant_id, is_active"],
    "dbp_compliance_checks": ["policy_id, status", "tenant_id"],
    "dbp_compliance_violations": ["tenant_id, status", "policy_id", "assigned_to"],
    "dbp_compliance_audit_log": ["tenant_id, created_at"],
    "dbp_compliance_frameworks": ["tenant_id, framework_type"],
}

if __name__ == "__main__":
    print("Running P46 migration...")
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

    print("P46 migration complete.")
