"""
P26 Migration — Sales & Invoicing
  - dbp_customers
  - dbp_sales_quotations
  - dbp_sales_quotation_lines
  - dbp_sales_orders
  - dbp_sales_order_lines
  - dbp_sales_invoices
  - dbp_sales_invoice_lines
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_customers": {
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
        "credit_limit": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_sales_quotations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "quote_number": "VARCHAR(50) NOT NULL",
        "customer_id": "VARCHAR(36) REFERENCES dbp_customers(id)",
        "quote_date": "DATE NOT NULL",
        "valid_until": "DATE",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_amount": "NUMERIC(18,4) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "notes": "TEXT",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_sales_quotation_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "quote_id": "VARCHAR(36) REFERENCES dbp_sales_quotations(id) ON DELETE CASCADE",
        "line_number": "INT NOT NULL",
        "item_id": "VARCHAR(36)",
        "description": "VARCHAR(500)",
        "quantity": "NUMERIC(18,4) NOT NULL",
        "unit_price": "NUMERIC(18,4) NOT NULL",
        "line_total": "NUMERIC(18,4) NOT NULL",
        "tax_rate": "NUMERIC(6,2) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
    },
    "dbp_sales_orders": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "order_number": "VARCHAR(50) NOT NULL",
        "customer_id": "VARCHAR(36) REFERENCES dbp_customers(id)",
        "quotation_id": "VARCHAR(36)",
        "order_date": "DATE NOT NULL",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_amount": "NUMERIC(18,4) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "notes": "TEXT",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_sales_order_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "order_id": "VARCHAR(36) REFERENCES dbp_sales_orders(id) ON DELETE CASCADE",
        "line_number": "INT NOT NULL",
        "item_id": "VARCHAR(36)",
        "description": "VARCHAR(500)",
        "quantity": "NUMERIC(18,4) NOT NULL",
        "unit_price": "NUMERIC(18,4) NOT NULL",
        "line_total": "NUMERIC(18,4) NOT NULL",
        "quantity_delivered": "NUMERIC(18,4) DEFAULT 0",
        "tax_rate": "NUMERIC(6,2) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
    },
    "dbp_sales_invoices": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "invoice_number": "VARCHAR(50) NOT NULL",
        "customer_id": "VARCHAR(36) REFERENCES dbp_customers(id)",
        "order_id": "VARCHAR(36)",
        "invoice_date": "DATE NOT NULL",
        "due_date": "DATE",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_amount": "NUMERIC(18,4) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
        "paid_amount": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "notes": "TEXT",
        "journal_entry_id": "VARCHAR(36)",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_sales_invoice_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "invoice_id": "VARCHAR(36) REFERENCES dbp_sales_invoices(id) ON DELETE CASCADE",
        "line_number": "INT NOT NULL",
        "item_id": "VARCHAR(36)",
        "description": "VARCHAR(500)",
        "quantity": "NUMERIC(18,4) NOT NULL",
        "unit_price": "NUMERIC(18,4) NOT NULL",
        "line_total": "NUMERIC(18,4) NOT NULL",
        "tax_rate": "NUMERIC(6,2) DEFAULT 0",
        "tax_amount": "NUMERIC(18,4) DEFAULT 0",
    },
}

INDEXES = {
    "dbp_customers": ["tenant_id", "company_id"],
    "dbp_sales_quotations": ["tenant_id", "company_id", "customer_id", "status"],
    "dbp_sales_quotation_lines": ["quote_id"],
    "dbp_sales_orders": ["tenant_id", "company_id", "customer_id", "status"],
    "dbp_sales_order_lines": ["order_id"],
    "dbp_sales_invoices": ["tenant_id", "company_id", "customer_id", "status"],
    "dbp_sales_invoice_lines": ["invoice_id"],
}

if __name__ == "__main__":
    print("Running P26 migration...")
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
    print("P26 migration complete.")
