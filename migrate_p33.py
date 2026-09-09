"""
P33 Migration - E-Signature & Enhanced Approval Workflows
  - dbp_signature_requests
  - dbp_signature_signers
  - dbp_approval_templates
  - dbp_approval_template_steps
  - dbp_delegations
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_signature_requests": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "reference_type": "VARCHAR(50)",
        "reference_id": "VARCHAR(36)",
        "title": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "requested_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "completed_at": "TIMESTAMPTZ",
    },
    "dbp_signature_signers": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "request_id": "VARCHAR(36) REFERENCES dbp_signature_requests(id) ON DELETE CASCADE",
        "signer_id": "VARCHAR(100) NOT NULL",
        "signer_email": "VARCHAR(255)",
        "signer_name": "VARCHAR(255)",
        "order_number": "INT DEFAULT 1",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "signature_data": "TEXT",
        "signed_at": "TIMESTAMPTZ",
        "rejection_reason": "TEXT",
    },
    "dbp_approval_templates": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "entity_type": "VARCHAR(100)",
        "description": "TEXT",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_approval_template_steps": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "template_id": "VARCHAR(36) REFERENCES dbp_approval_templates(id) ON DELETE CASCADE",
        "step_number": "INT NOT NULL",
        "approver_role": "VARCHAR(100)",
        "approver_id": "VARCHAR(100)",
        "sla_hours": "INT DEFAULT 48",
        "auto_approve": "BOOLEAN DEFAULT false",
    },
    "dbp_delegations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "delegator_id": "VARCHAR(100) NOT NULL",
        "delegate_id": "VARCHAR(100) NOT NULL",
        "entity_type": "VARCHAR(100)",
        "start_date": "DATE NOT NULL",
        "end_date": "DATE NOT NULL",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_signature_requests": ["tenant_id, company_id"],
    "dbp_signature_signers": ["request_id"],
    "dbp_approval_templates": ["tenant_id, company_id"],
    "dbp_approval_template_steps": ["template_id"],
    "dbp_delegations": ["tenant_id, company_id"],
}

if __name__ == "__main__":
    print("Running P33 migration...")
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

    print("P33 migration complete.")
