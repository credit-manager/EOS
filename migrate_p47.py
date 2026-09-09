"""
P47 Identity Federation & SSO Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_sso_providers": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "provider_name": "VARCHAR(100) NOT NULL",
        "provider_type": "VARCHAR(30) NOT NULL",
        "client_id": "VARCHAR(200) NOT NULL",
        "client_secret_enc": "TEXT",
        "metadata_url": "TEXT",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_sso_sessions": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "user_id": "VARCHAR(36) NOT NULL",
        "provider_id": "VARCHAR(36) NOT NULL",
        "sso_session_id": "VARCHAR(200)",
        "ip_address": "VARCHAR(45)",
        "user_agent": "TEXT",
        "expires_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_mfa_configs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "user_id": "VARCHAR(36) NOT NULL",
        "mfa_type": "VARCHAR(30) NOT NULL",
        "secret_enc": "TEXT",
        "is_enabled": "BOOLEAN DEFAULT false",
        "last_used_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_role_mappings": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "provider_id": "VARCHAR(36) NOT NULL",
        "external_role": "VARCHAR(100) NOT NULL",
        "internal_role": "VARCHAR(50) NOT NULL",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_api_keys": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "key_name": "VARCHAR(100) NOT NULL",
        "key_hash": "VARCHAR(200) NOT NULL",
        "permissions": "JSONB",
        "expires_at": "TIMESTAMPTZ",
        "is_active": "BOOLEAN DEFAULT true",
        "last_used_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_sso_providers": ["tenant_id, is_active"],
    "dbp_sso_sessions": ["tenant_id, user_id", "provider_id"],
    "dbp_mfa_configs": ["tenant_id, user_id"],
    "dbp_role_mappings": ["tenant_id, provider_id"],
    "dbp_api_keys": ["tenant_id, is_active", "key_hash"],
}

if __name__ == "__main__":
    print("Running P47 migration...")
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

    print("P47 migration complete.")
