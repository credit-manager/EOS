"""
P24 Migration — Procurement & Purchase Orders
  - dbp_items
  - dbp_suppliers
  - dbp_purchase_requests
  - dbp_purchase_order_lines
  - dbp_purchase_orders
  - dbp_grn_items (Goods Received Note)
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_items": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "item_type": "VARCHAR(30) NOT NULL",
        "category": "VARCHAR(100)",
        "unit_of_measure": "VARCHAR(30)",
        "standard_cost": "NUMERIC(18,4) DEFAULT 0",
        "gl_account_id": "VARCHAR(36)",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_suppliers": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "contact_name": "VARCHAR(255)",
        "email": "VARCHAR(255)",
        "phone": "VARCHAR(50)",
        "address": "TEXT",
        "tax_number": "VARCHAR(50)",
        "payment_terms": "VARCHAR(30)",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "gl_account_id": "VARCHAR(36)",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_purchase_requests": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "request_number": "VARCHAR(50) NOT NULL",
        "request_date": "DATE NOT NULL",
        "requester_id": "VARCHAR(100)",
        "department_id": "VARCHAR(36)",
        "description": "TEXT",
        "priority": "VARCHAR(20) DEFAULT 'normal'",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "approved_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_purchase_orders": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "order_number": "VARCHAR(50) NOT NULL",
        "supplier_id": "VARCHAR(36) REFERENCES dbp_suppliers(id)",
        "request_id": "VARCHAR(36)",
        "order_date": "DATE NOT NULL",
        "expected_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_amount": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
        "discount_amount": "NUMERIC(18,4) DEFAULT 0",
        "notes": "TEXT",
        "approved_by": "VARCHAR(100)",
        "created_by": "VARCHAR(100)",
        "cost_center_id": "VARCHAR(36)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_purchase_order_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "order_id": "VARCHAR(36) REFERENCES dbp_purchase_orders(id) ON DELETE CASCADE",
        "line_number": "INT NOT NULL",
        "item_id": "VARCHAR(36) REFERENCES dbp_items(id)",
        "description": "VARCHAR(500)",
        "quantity": "NUMERIC(18,4) NOT NULL",
        "unit_price": "NUMERIC(18,4) NOT NULL",
        "line_total": "NUMERIC(18,4) NOT NULL",
        "quantity_received": "NUMERIC(18,4) DEFAULT 0",
        "tax_rate": "NUMERIC(6,2) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
    },
    "dbp_grn_items": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "order_id": "VARCHAR(36) REFERENCES dbp_purchase_orders(id)",
        "line_id": "VARCHAR(36) REFERENCES dbp_purchase_order_lines(id)",
        "quantity_received": "NUMERIC(18,4) NOT NULL",
        "received_date": "DATE NOT NULL",
        "received_by": "VARCHAR(100)",
        "notes": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_items": ["tenant_id", "company_id", "code"],
    "dbp_suppliers": ["tenant_id", "company_id"],
    "dbp_purchase_requests": ["tenant_id", "company_id", "status"],
    "dbp_purchase_orders": ["tenant_id", "company_id", "status", "supplier_id"],
    "dbp_purchase_order_lines": ["order_id"],
    "dbp_grn_items": ["order_id", "line_id"],
}

if __name__ == "__main__":
    print("Running P24 migration...")
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
    print("P24 migration complete.")
