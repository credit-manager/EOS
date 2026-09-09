"""
P25 Migration — Inventory Management
  - dbp_warehouses
  - dbp_stock
  - dbp_stock_movements
  - dbp_stock_takes
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_warehouses": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "location": "TEXT",
        "manager_id": "VARCHAR(100)",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_stock": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "item_id": "VARCHAR(36) NOT NULL",
        "warehouse_id": "VARCHAR(36) NOT NULL",
        "quantity_on_hand": "NUMERIC(18,4) DEFAULT 0",
        "quantity_reserved": "NUMERIC(18,4) DEFAULT 0",
        "reorder_level": "NUMERIC(18,4) DEFAULT 0",
        "max_level": "NUMERIC(18,4) DEFAULT 0",
        "last_counted_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_stock_movements": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "item_id": "VARCHAR(36) NOT NULL",
        "warehouse_id": "VARCHAR(36) NOT NULL",
        "movement_type": "VARCHAR(30) NOT NULL",
        "quantity": "NUMERIC(18,4) NOT NULL",
        "reference_type": "VARCHAR(50)",
        "reference_id": "VARCHAR(36)",
        "notes": "TEXT",
        "moved_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_stock_takes": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "warehouse_id": "VARCHAR(36) NOT NULL",
        "take_number": "VARCHAR(50) NOT NULL",
        "take_date": "DATE NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'in_progress'",
        "notes": "TEXT",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_warehouses": ["tenant_id", "company_id"],
    "dbp_stock": ["tenant_id", "company_id", "item_id", "warehouse_id"],
    "dbp_stock_movements": ["tenant_id", "company_id", "item_id", "warehouse_id", "movement_type", "created_at"],
    "dbp_stock_takes": ["tenant_id", "company_id", "warehouse_id"],
}

if __name__ == "__main__":
    print("Running P25 migration...")
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
    print("P25 migration complete.")
