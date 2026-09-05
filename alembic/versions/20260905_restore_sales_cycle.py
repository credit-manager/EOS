"""Restore the transactional Sales CRM schema required by the commercial API.

The runtime SalesEngine uses dbp_* tables, while the legacy migration only
hardened unrelated customers/leads/opportunities tables. Fresh databases
therefore reached Alembic head without the tables required by the product.
"""
from alembic import op

revision = "20260905_restore_sales_cycle"
down_revision = "20260905_restore_refresh_tokens"
branch_labels = None
depends_on = None


_TABLES = (
    "dbp_sales_invoice_lines",
    "dbp_sales_invoices",
    "dbp_sales_order_lines",
    "dbp_sales_orders",
    "dbp_sales_quotation_lines",
    "dbp_sales_quotations",
    "dbp_customers",
)


def _rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table}" ON {table}')
    op.execute(
        f'''CREATE POLICY "tenant_isolation_{table}" ON {table}
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))'''
    )


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_customers (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            company_id VARCHAR(36) NOT NULL,
            code VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            contact_name VARCHAR(255),
            email VARCHAR(320),
            phone VARCHAR(64),
            address TEXT,
            tax_number VARCHAR(128),
            payment_terms VARCHAR(64) DEFAULT 'net30',
            credit_limit NUMERIC(18,4) NOT NULL DEFAULT 0,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'SAR',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_customers_company_code UNIQUE (company_id, code)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_quotations (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            company_id VARCHAR(36) NOT NULL,
            quote_number VARCHAR(64) NOT NULL,
            customer_id VARCHAR(36) NOT NULL,
            quote_date DATE NOT NULL,
            valid_until DATE,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'SAR',
            notes TEXT,
            created_by VARCHAR(36),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_quotations_company_number UNIQUE (company_id, quote_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_quotation_lines (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            quote_id VARCHAR(36) NOT NULL,
            line_number INTEGER NOT NULL,
            item_id VARCHAR(36),
            description TEXT,
            quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
            unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
            line_total NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_quote_lines_number UNIQUE (quote_id, line_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_orders (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            company_id VARCHAR(36) NOT NULL,
            order_number VARCHAR(64) NOT NULL,
            customer_id VARCHAR(36) NOT NULL,
            quotation_id VARCHAR(36),
            order_date DATE NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'SAR',
            notes TEXT,
            created_by VARCHAR(36),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_orders_company_number UNIQUE (company_id, order_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_order_lines (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            order_id VARCHAR(36) NOT NULL,
            line_number INTEGER NOT NULL,
            item_id VARCHAR(36),
            description TEXT,
            quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
            unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
            line_total NUMERIC(18,4) NOT NULL DEFAULT 0,
            quantity_delivered NUMERIC(18,6) NOT NULL DEFAULT 0,
            tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_order_lines_number UNIQUE (order_id, line_number)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_invoices (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            company_id VARCHAR(36) NOT NULL,
            invoice_number VARCHAR(64) NOT NULL,
            customer_id VARCHAR(36) NOT NULL,
            order_id VARCHAR(36),
            invoice_date DATE NOT NULL,
            due_date DATE,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            total_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            paid_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'SAR',
            notes TEXT,
            created_by VARCHAR(36),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_invoices_company_number UNIQUE (company_id, invoice_number),
            CONSTRAINT ck_dbp_sales_invoice_paid_nonnegative CHECK (paid_amount >= 0),
            CONSTRAINT ck_dbp_sales_invoice_total_nonnegative CHECK (total_amount >= 0),
            CONSTRAINT ck_dbp_sales_invoice_tax_nonnegative CHECK (tax_amount >= 0)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_sales_invoice_lines (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            invoice_id VARCHAR(36) NOT NULL,
            line_number INTEGER NOT NULL,
            item_id VARCHAR(36),
            description TEXT,
            quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
            unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
            line_total NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_rate NUMERIC(9,4) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(18,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_dbp_sales_invoice_lines_number UNIQUE (invoice_id, line_number)
        )
    """)

    for table in _TABLES:
        op.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table} (tenant_id)")
        _rls(table)

    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_quotations_company_date ON dbp_sales_quotations (company_id, quote_date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_orders_company_date ON dbp_sales_orders (company_id, order_date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_invoices_company_date ON dbp_sales_invoices (company_id, invoice_date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_invoice_lines_invoice ON dbp_sales_invoice_lines (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_order_lines_order ON dbp_sales_order_lines (order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dbp_sales_quote_lines_quote ON dbp_sales_quotation_lines (quote_id)")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table}" ON {table}')
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in _TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
