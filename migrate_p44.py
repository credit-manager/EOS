"""
P44 Multi-Region & Edge Deployment Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_edge_nodes": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "node_name": "VARCHAR(100) NOT NULL",
        "region": "VARCHAR(50) NOT NULL",
        "endpoint_url": "VARCHAR(300) NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "latency_ms": "DOUBLE PRECISION",
        "capacity_pct": "DOUBLE PRECISION DEFAULT 0",
        "metadata": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_region_configs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "region": "VARCHAR(50) NOT NULL",
        "is_primary": "BOOLEAN DEFAULT false",
        "data_residency": "VARCHAR(50)",
        "replication_mode": "VARCHAR(30) DEFAULT 'async'",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_edge_sync_log": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "node_id": "VARCHAR(36) NOT NULL",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "sync_type": "VARCHAR(30) NOT NULL",
        "entity_type": "VARCHAR(50)",
        "entity_id": "VARCHAR(36)",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "retry_count": "INT DEFAULT 0",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "completed_at": "TIMESTAMPTZ",
    },
    "dbp_network_topology": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "node_id": "VARCHAR(36) NOT NULL",
        "peer_node_id": "VARCHAR(36) NOT NULL",
        "link_type": "VARCHAR(30) DEFAULT 'mesh'",
        "bandwidth_mbps": "INT",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_region_failover": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "source_region": "VARCHAR(50) NOT NULL",
        "target_region": "VARCHAR(50) NOT NULL",
        "trigger_reason": "VARCHAR(100)",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "activated_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_edge_nodes": ["region, status"],
    "dbp_region_configs": ["tenant_id, region"],
    "dbp_edge_sync_log": ["node_id, status", "tenant_id, created_at"],
    "dbp_network_topology": ["node_id"],
    "dbp_region_failover": ["tenant_id, status"],
}

if __name__ == "__main__":
    print("Running P44 migration...")
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

    print("P44 migration complete.")
