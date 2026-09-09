"""
P29 Migration — Fixed Assets Management
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_fixed_assets": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "asset_code": "VARCHAR(50) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "description": "TEXT",
        "category": "VARCHAR(100)",
        "acquisition_date": "DATE NOT NULL",
        "acquisition_cost": "NUMERIC(18,4) NOT NULL",
        "salvage_value": "NUMERIC(18,4) DEFAULT 0",
        "useful_life_years": "INT NOT NULL",
        "depreciation_method": "VARCHAR(20) DEFAULT 'straight_line'",
        "accumulated_depreciation": "NUMERIC(18,4) DEFAULT 0",
        "book_value": "NUMERIC(18,4) DEFAULT 0",
        "location": "VARCHAR(255)",
        "warehouse_id": "VARCHAR(36)",
        "employee_id": "VARCHAR(100)",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "gl_account_id": "VARCHAR(36)",
        "depreciation_gl_account_id": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_asset_depreciation_runs": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "period_start": "DATE NOT NULL",
        "period_end": "DATE NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_depreciation": "NUMERIC(18,4) DEFAULT 0",
        "processed_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_asset_depreciation_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "run_id": "VARCHAR(36)",
        "asset_id": "VARCHAR(36) NOT NULL",
        "depreciation_amount": "NUMERIC(18,4) NOT NULL",
        "accumulated_after": "NUMERIC(18,4) NOT NULL",
        "book_value_after": "NUMERIC(18,4) NOT NULL",
    },
    "dbp_asset_transfers": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "asset_id": "VARCHAR(36) NOT NULL",
        "from_location": "VARCHAR(255)",
        "to_location": "VARCHAR(255)",
        "transfer_date": "DATE",
        "transferred_by": "VARCHAR(100)",
        "notes": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_fixed_assets": ["tenant_id", "company_id", "status"],
    "dbp_asset_depreciation_runs": ["tenant_id", "company_id"],
    "dbp_asset_depreciation_lines": ["run_id", "asset_id"],
    "dbp_asset_transfers": ["asset_id"],
}

if __name__ == "__main__":
    print("Running P29 migration...")
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
    print("P29 migration complete.")
