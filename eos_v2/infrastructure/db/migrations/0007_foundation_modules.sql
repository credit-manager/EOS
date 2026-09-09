-- EOS DBP v2 foundation ERP module schema.
-- Operational data is tenant-scoped and isolated from legacy tables.
CREATE TABLE IF NOT EXISTS eos_v2_sales_orders (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    lines JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_sales_orders_tenant ON eos_v2_sales_orders(tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_purchase_orders (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    supplier_id UUID NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    lines JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_purchase_orders_tenant ON eos_v2_purchase_orders(tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_inventory_movements (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    item_id UUID NOT NULL,
    quantity NUMERIC(20,6) NOT NULL,
    source VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_inventory_movements_tenant ON eos_v2_inventory_movements(tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_stock_balances (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    item_id UUID NOT NULL,
    quantity NUMERIC(20,6) NOT NULL,
    CONSTRAINT uq_eos_v2_stock_balance UNIQUE (tenant_id, item_id),
    CONSTRAINT ck_eos_v2_stock_nonnegative CHECK (quantity >= 0)
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_stock_balances_tenant ON eos_v2_stock_balances(tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_employees (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    employee_number VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    hire_date DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_eos_v2_employee_number UNIQUE (tenant_id, employee_number)
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_employees_tenant ON eos_v2_employees(tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_projects (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT uq_eos_v2_project_code UNIQUE (tenant_id, code),
    CONSTRAINT ck_eos_v2_project_dates CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_projects_tenant ON eos_v2_projects(tenant_id);
