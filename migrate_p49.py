"""
P49 Blockchain & Immutable Audit Trail Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_blockchain_records": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "entity_type": "VARCHAR(100) NOT NULL",
        "entity_id": "VARCHAR(36) NOT NULL",
        "content_hash": "VARCHAR(128) NOT NULL",
        "previous_hash": "VARCHAR(128)",
        "block_number": "BIGINT NOT NULL",
        "chain_id": "VARCHAR(50) NOT NULL",
        "metadata": "JSONB",
        "recorded_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_blockchain_chains": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "chain_name": "VARCHAR(100) NOT NULL",
        "chain_type": "VARCHAR(30) NOT NULL",
        "consensus": "VARCHAR(30)",
        "node_count": "INT DEFAULT 1",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "config": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_blockchain_nodes": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "chain_id": "VARCHAR(36) NOT NULL",
        "node_name": "VARCHAR(100) NOT NULL",
        "node_url": "VARCHAR(300) NOT NULL",
        "role": "VARCHAR(30) DEFAULT 'follower'",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "last_sync_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_blockchain_verification": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "record_id": "VARCHAR(36) NOT NULL",
        "verification_result": "BOOLEAN NOT NULL",
        "verified_at": "TIMESTAMPTZ DEFAULT NOW()",
        "verified_by": "VARCHAR(36)",
    },
    "dbp_immutable_audit": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "entity_type": "VARCHAR(100) NOT NULL",
        "entity_id": "VARCHAR(36) NOT NULL",
        "action": "VARCHAR(50) NOT NULL",
        "actor_id": "VARCHAR(36)",
        "before_data": "JSONB",
        "after_data": "JSONB",
        "content_hash": "VARCHAR(128) NOT NULL",
        "blockchain_record_id": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_blockchain_records": ["tenant_id, entity_type, entity_id", "block_number"],
    "dbp_blockchain_chains": ["tenant_id, chain_type"],
    "dbp_blockchain_nodes": ["chain_id"],
    "dbp_blockchain_verification": ["tenant_id, record_id"],
    "dbp_immutable_audit": ["tenant_id, entity_type, entity_id", "created_at"],
}

if __name__ == "__main__":
    print("Running P49 migration...")
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

    print("P49 migration complete.")
