"""
P70.4 Trading ERP Professional — Database Migration
=====================================================
Creates all trading-specific tables on top of the shared security foundation.
Uses p703a_hardening.py patterns (FK, UNIQUE, CHECK, triggers).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from sqlalchemy import text

TENANT_ID = "f57e6756-b954-4ade-a17b-f2125e4b97c4"

TABLES = [
    # ═══════════════════════════════════════════
    # ITEMS & INVENTORY
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        item_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        description TEXT,
        description_ar TEXT,
        category VARCHAR(100),
        unit VARCHAR(50) NOT NULL DEFAULT 'piece',
        cost_price NUMERIC(15,4) DEFAULT 0,
        selling_price NUMERIC(15,4) DEFAULT 0,
        min_stock NUMERIC(15,4) DEFAULT 0,
        max_stock NUMERIC(15,4) DEFAULT 999999,
        reorder_point NUMERIC(15,4) DEFAULT 0,
        has_batch BOOLEAN DEFAULT false,
        has_serial BOOLEAN DEFAULT false,
        has_expiry BOOLEAN DEFAULT false,
        weight NUMERIC(10,4),
        barcode VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_stock (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        warehouse_id VARCHAR(36) NOT NULL,
        on_hand NUMERIC(15,4) DEFAULT 0,
        reserved NUMERIC(15,4) DEFAULT 0,
        in_transit NUMERIC(15,4) DEFAULT 0,
        unit_cost NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_warehouses (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        address TEXT,
        manager VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # CUSTOMERS & SUPPLIERS
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_customers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        customer_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        contact_person VARCHAR(100),
        email VARCHAR(150),
        phone VARCHAR(50),
        address TEXT,
        credit_limit NUMERIC(15,4) DEFAULT 0,
        current_balance NUMERIC(15,4) DEFAULT 0,
        territory VARCHAR(100),
        salesman VARCHAR(100),
        payment_terms VARCHAR(50) DEFAULT 'net30',
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_suppliers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        supplier_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        contact_person VARCHAR(100),
        email VARCHAR(150),
        phone VARCHAR(50),
        address TEXT,
        payment_terms VARCHAR(50) DEFAULT 'net30',
        lead_time_days INT DEFAULT 7,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # SALES CYCLE
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_quotations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        quote_number VARCHAR(50) NOT NULL,
        customer_id VARCHAR(36) NOT NULL,
        quote_date DATE DEFAULT CURRENT_DATE,
        valid_until DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_rate NUMERIC(5,2) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        discount_rate NUMERIC(5,2) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'draft',
        created_by VARCHAR(100),
        approved_by VARCHAR(100),
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_quotation_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        quotation_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        description VARCHAR(500),
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_sales_orders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        so_number VARCHAR(50) NOT NULL,
        customer_id VARCHAR(36) NOT NULL,
        quotation_id VARCHAR(36),
        order_date DATE DEFAULT CURRENT_DATE,
        delivery_date DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_rate NUMERIC(5,2) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        discount_rate NUMERIC(5,2) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'draft',
        delivery_status VARCHAR(20) DEFAULT 'pending',
        invoice_status VARCHAR(20) DEFAULT 'uninvoiced',
        created_by VARCHAR(100),
        approved_by VARCHAR(100),
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_sales_order_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        so_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        description VARCHAR(500),
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        delivered_qty NUMERIC(15,4) DEFAULT 0,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        cost_price NUMERIC(15,4) DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_delivery_notes (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        dn_number VARCHAR(50) NOT NULL,
        so_id VARCHAR(36) NOT NULL,
        customer_id VARCHAR(36) NOT NULL,
        delivery_date DATE DEFAULT CURRENT_DATE,
        driver_name VARCHAR(100),
        vehicle_number VARCHAR(50),
        notes TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        received_by VARCHAR(100),
        received_at TIMESTAMPTZ,
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_delivery_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        dn_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        received_qty NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_sales_invoices (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        invoice_number VARCHAR(50) NOT NULL,
        so_id VARCHAR(36),
        dn_id VARCHAR(36),
        customer_id VARCHAR(36) NOT NULL,
        invoice_date DATE DEFAULT CURRENT_DATE,
        due_date DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_rate NUMERIC(5,2) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        paid_amount NUMERIC(15,4) DEFAULT 0,
        balance NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'unpaid',
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_customer_payments (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        payment_number VARCHAR(50) NOT NULL,
        customer_id VARCHAR(36) NOT NULL,
        invoice_id VARCHAR(36),
        payment_date DATE DEFAULT CURRENT_DATE,
        amount NUMERIC(15,4) NOT NULL DEFAULT 0,
        payment_method VARCHAR(50) DEFAULT 'cash',
        reference VARCHAR(100),
        notes TEXT,
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # PURCHASE CYCLE
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_requests (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        pr_number VARCHAR(50) NOT NULL,
        requested_by VARCHAR(100),
        request_date DATE DEFAULT CURRENT_DATE,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'draft',
        approved_by VARCHAR(100),
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_request_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        pr_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        estimated_price NUMERIC(15,4) DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_rfqs (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        rfq_number VARCHAR(50) NOT NULL,
        pr_id VARCHAR(36),
        supplier_id VARCHAR(36) NOT NULL,
        rfq_date DATE DEFAULT CURRENT_DATE,
        valid_until DATE,
        status VARCHAR(20) DEFAULT 'sent',
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_rfq_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        rfq_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_supplier_quotations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        sq_number VARCHAR(50) NOT NULL,
        rfq_id VARCHAR(36),
        supplier_id VARCHAR(36) NOT NULL,
        quote_date DATE DEFAULT CURRENT_DATE,
        valid_until DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'received',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_supplier_quotation_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        sq_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_orders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        po_number VARCHAR(50) NOT NULL,
        supplier_id VARCHAR(36) NOT NULL,
        sq_id VARCHAR(36),
        order_date DATE DEFAULT CURRENT_DATE,
        expected_date DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_rate NUMERIC(5,2) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'draft',
        grn_status VARCHAR(20) DEFAULT 'pending',
        invoice_status VARCHAR(20) DEFAULT 'uninvoiced',
        created_by VARCHAR(100),
        approved_by VARCHAR(100),
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_order_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        po_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        received_qty NUMERIC(15,4) DEFAULT 0,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_grn (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        grn_number VARCHAR(50) NOT NULL,
        po_id VARCHAR(36) NOT NULL,
        supplier_id VARCHAR(36) NOT NULL,
        grn_date DATE DEFAULT CURRENT_DATE,
        received_by VARCHAR(100),
        notes TEXT,
        status VARCHAR(20) DEFAULT 'received',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_grn_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        grn_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        po_line_id VARCHAR(36),
        qty_received NUMERIC(15,4) NOT NULL DEFAULT 0,
        qty_accepted NUMERIC(15,4) DEFAULT 0,
        qty_rejected NUMERIC(15,4) DEFAULT 0,
        unit_cost NUMERIC(15,4) DEFAULT 0,
        batch_number VARCHAR(100),
        expiry_date DATE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_invoices (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        invoice_number VARCHAR(50) NOT NULL,
        po_id VARCHAR(36),
        grn_id VARCHAR(36),
        supplier_id VARCHAR(36) NOT NULL,
        invoice_date DATE DEFAULT CURRENT_DATE,
        due_date DATE,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        paid_amount NUMERIC(15,4) DEFAULT 0,
        balance NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'unpaid',
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_supplier_payments (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        payment_number VARCHAR(50) NOT NULL,
        supplier_id VARCHAR(36) NOT NULL,
        invoice_id VARCHAR(36),
        payment_date DATE DEFAULT CURRENT_DATE,
        amount NUMERIC(15,4) NOT NULL DEFAULT 0,
        payment_method VARCHAR(50) DEFAULT 'bank_transfer',
        reference VARCHAR(100),
        notes TEXT,
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # PRICING
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_price_lists (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        list_name VARCHAR(100) NOT NULL,
        description TEXT,
        currency VARCHAR(10) DEFAULT 'EGP',
        is_default BOOLEAN DEFAULT false,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_price_list_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        price_list_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        selling_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        min_qty NUMERIC(15,4) DEFAULT 1,
        valid_from DATE DEFAULT CURRENT_DATE,
        valid_until DATE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # SALES RETURNS
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_sales_returns (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        return_number VARCHAR(50) NOT NULL,
        invoice_id VARCHAR(36),
        customer_id VARCHAR(36) NOT NULL,
        return_date DATE DEFAULT CURRENT_DATE,
        reason TEXT,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_sales_return_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        return_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        unit_price NUMERIC(15,4) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # PURCHASE RETURNS
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_returns (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        return_number VARCHAR(50) NOT NULL,
        invoice_id VARCHAR(36),
        supplier_id VARCHAR(36) NOT NULL,
        return_date DATE DEFAULT CURRENT_DATE,
        reason TEXT,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        journal_entry_id VARCHAR(36),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_purchase_return_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        return_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        unit_price NUMERIC(15,4) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # STOCK TRANSFERS & ADJUSTMENTS
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_stock_transfers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        transfer_number VARCHAR(50) NOT NULL,
        from_warehouse_id VARCHAR(36) NOT NULL,
        to_warehouse_id VARCHAR(36) NOT NULL,
        transfer_date DATE DEFAULT CURRENT_DATE,
        status VARCHAR(20) DEFAULT 'pending',
        notes TEXT,
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_stock_transfer_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        transfer_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 0,
        received_qty NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_stock_adjustments (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        adj_number VARCHAR(50) NOT NULL,
        warehouse_id VARCHAR(36) NOT NULL,
        adjustment_date DATE DEFAULT CURRENT_DATE,
        reason TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        approved_by VARCHAR(100),
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_stock_adjustment_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        adjustment_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty_before NUMERIC(15,4) DEFAULT 0,
        qty_after NUMERIC(15,4) DEFAULT 0,
        qty_adjusted NUMERIC(15,4) DEFAULT 0,
        unit_cost NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # ═══════════════════════════════════════════
    # SALES & TERRITORIES
    # ═══════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_salesmen (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        code VARCHAR(50) NOT NULL,
        territory VARCHAR(100),
        phone VARCHAR(50),
        email VARCHAR(150),
        commission_rate NUMERIC(5,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_trading_territories (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        parent_id VARCHAR(36),
        manager VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]

CONSTRAINTS = [
    # FK constraints
    "ALTER TABLE dbp_trading_stock ADD CONSTRAINT fk_trd_stock_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_stock ADD CONSTRAINT fk_trd_stock_wh FOREIGN KEY (warehouse_id) REFERENCES dbp_trading_warehouses(id)",
    "ALTER TABLE dbp_trading_quotation_lines ADD CONSTRAINT fk_trd_ql_quotation FOREIGN KEY (quotation_id) REFERENCES dbp_trading_quotations(id)",
    "ALTER TABLE dbp_trading_quotation_lines ADD CONSTRAINT fk_trd_ql_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_sales_order_lines ADD CONSTRAINT fk_trd_sol_so FOREIGN KEY (so_id) REFERENCES dbp_trading_sales_orders(id)",
    "ALTER TABLE dbp_trading_sales_order_lines ADD CONSTRAINT fk_trd_sol_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_delivery_lines ADD CONSTRAINT fk_trd_dl_dn FOREIGN KEY (dn_id) REFERENCES dbp_trading_delivery_notes(id)",
    "ALTER TABLE dbp_trading_delivery_lines ADD CONSTRAINT fk_trd_dl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT fk_trd_si_so FOREIGN KEY (so_id) REFERENCES dbp_trading_sales_orders(id)",
    "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT fk_trd_si_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
    "ALTER TABLE dbp_trading_customer_payments ADD CONSTRAINT fk_trd_cp_invoice FOREIGN KEY (invoice_id) REFERENCES dbp_trading_sales_invoices(id)",
    "ALTER TABLE dbp_trading_purchase_request_lines ADD CONSTRAINT fk_trd_prl_pr FOREIGN KEY (pr_id) REFERENCES dbp_trading_purchase_requests(id)",
    "ALTER TABLE dbp_trading_purchase_request_lines ADD CONSTRAINT fk_trd_prl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_rfq_lines ADD CONSTRAINT fk_trd_rfl_rfq FOREIGN KEY (rfq_id) REFERENCES dbp_trading_rfqs(id)",
    "ALTER TABLE dbp_trading_supplier_quotation_lines ADD CONSTRAINT fk_trd_sql_sq FOREIGN KEY (sq_id) REFERENCES dbp_trading_supplier_quotations(id)",
    "ALTER TABLE dbp_trading_purchase_order_lines ADD CONSTRAINT fk_trd_pol_po FOREIGN KEY (po_id) REFERENCES dbp_trading_purchase_orders(id)",
    "ALTER TABLE dbp_trading_purchase_order_lines ADD CONSTRAINT fk_trd_pol_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT fk_trd_gl_grn FOREIGN KEY (grn_id) REFERENCES dbp_trading_grn(id)",
    "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT fk_trd_gl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT fk_trd_pi_po FOREIGN KEY (po_id) REFERENCES dbp_trading_purchase_orders(id)",
    "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT fk_trd_pi_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
    "ALTER TABLE dbp_trading_supplier_payments ADD CONSTRAINT fk_trd_sp_invoice FOREIGN KEY (invoice_id) REFERENCES dbp_trading_purchase_invoices(id)",
    "ALTER TABLE dbp_trading_price_list_items ADD CONSTRAINT fk_trd_pli_list FOREIGN KEY (price_list_id) REFERENCES dbp_trading_price_lists(id)",
    "ALTER TABLE dbp_trading_price_list_items ADD CONSTRAINT fk_trd_pli_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
    "ALTER TABLE dbp_trading_sales_return_lines ADD CONSTRAINT fk_trd_srl_return FOREIGN KEY (return_id) REFERENCES dbp_trading_sales_returns(id)",
    "ALTER TABLE dbp_trading_purchase_return_lines ADD CONSTRAINT fk_trd_prtl_return FOREIGN KEY (return_id) REFERENCES dbp_trading_purchase_returns(id)",
    "ALTER TABLE dbp_trading_stock_transfer_lines ADD CONSTRAINT fk_trd_stl_transfer FOREIGN KEY (transfer_id) REFERENCES dbp_trading_stock_transfers(id)",
    "ALTER TABLE dbp_trading_stock_adjustment_lines ADD CONSTRAINT fk_trd_sal_adj FOREIGN KEY (adjustment_id) REFERENCES dbp_trading_stock_adjustments(id)",
    # UNIQUE constraints (per tenant)
    "ALTER TABLE dbp_trading_items ADD CONSTRAINT uq_trd_item_tenant_code UNIQUE (tenant_id, item_code)",
    "ALTER TABLE dbp_trading_warehouses ADD CONSTRAINT uq_trd_wh_tenant_code UNIQUE (tenant_id, code)",
    "ALTER TABLE dbp_trading_customers ADD CONSTRAINT uq_trd_cust_tenant_code UNIQUE (tenant_id, customer_code)",
    "ALTER TABLE dbp_trading_suppliers ADD CONSTRAINT uq_trd_supp_tenant_code UNIQUE (tenant_id, supplier_code)",
    "ALTER TABLE dbp_trading_quotations ADD CONSTRAINT uq_trd_quot_tenant_number UNIQUE (tenant_id, quote_number)",
    "ALTER TABLE dbp_trading_sales_orders ADD CONSTRAINT uq_trd_so_tenant_number UNIQUE (tenant_id, so_number)",
    "ALTER TABLE dbp_trading_delivery_notes ADD CONSTRAINT uq_trd_dn_tenant_number UNIQUE (tenant_id, dn_number)",
    "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT uq_trd_si_tenant_number UNIQUE (tenant_id, invoice_number)",
    "ALTER TABLE dbp_trading_customer_payments ADD CONSTRAINT uq_trd_cp_tenant_number UNIQUE (tenant_id, payment_number)",
    "ALTER TABLE dbp_trading_purchase_requests ADD CONSTRAINT uq_trd_pr_tenant_number UNIQUE (tenant_id, pr_number)",
    "ALTER TABLE dbp_trading_rfqs ADD CONSTRAINT uq_trd_rfq_tenant_number UNIQUE (tenant_id, rfq_number)",
    "ALTER TABLE dbp_trading_supplier_quotations ADD CONSTRAINT uq_trd_sq_tenant_number UNIQUE (tenant_id, sq_number)",
    "ALTER TABLE dbp_trading_purchase_orders ADD CONSTRAINT uq_trd_po_tenant_number UNIQUE (tenant_id, po_number)",
    "ALTER TABLE dbp_trading_grn ADD CONSTRAINT uq_trd_grn_tenant_number UNIQUE (tenant_id, grn_number)",
    "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT uq_trd_pi_tenant_number UNIQUE (tenant_id, invoice_number)",
    "ALTER TABLE dbp_trading_supplier_payments ADD CONSTRAINT uq_trd_sp_tenant_number UNIQUE (tenant_id, payment_number)",
    "ALTER TABLE dbp_trading_sales_returns ADD CONSTRAINT uq_trd_sr_tenant_number UNIQUE (tenant_id, return_number)",
    "ALTER TABLE dbp_trading_purchase_returns ADD CONSTRAINT uq_trd_preturn_tenant_number UNIQUE (tenant_id, return_number)",
    "ALTER TABLE dbp_trading_stock_transfers ADD CONSTRAINT uq_trd_st_tenant_number UNIQUE (tenant_id, transfer_number)",
    "ALTER TABLE dbp_trading_stock_adjustments ADD CONSTRAINT uq_trd_sa_tenant_number UNIQUE (tenant_id, adj_number)",
    "ALTER TABLE dbp_trading_salesmen ADD CONSTRAINT uq_trd_sm_tenant_code UNIQUE (tenant_id, code)",
    # CHECK constraints
    "ALTER TABLE dbp_trading_stock ADD CONSTRAINT chk_trd_stock_onhand CHECK (on_hand >= 0)",
    "ALTER TABLE dbp_trading_stock ADD CONSTRAINT chk_trd_stock_reserved CHECK (reserved >= 0)",
    "ALTER TABLE dbp_trading_stock ADD CONSTRAINT chk_trd_stock_reserved_le CHECK (reserved <= on_hand)",
    "ALTER TABLE dbp_trading_items ADD CONSTRAINT chk_trd_item_cost CHECK (cost_price >= 0)",
    "ALTER TABLE dbp_trading_items ADD CONSTRAINT chk_trd_item_price CHECK (selling_price >= 0)",
    "ALTER TABLE dbp_trading_customers ADD CONSTRAINT chk_trd_cust_credit CHECK (credit_limit >= 0)",
    "ALTER TABLE dbp_trading_quotations ADD CONSTRAINT chk_trd_quot_total CHECK (total >= 0)",
    "ALTER TABLE dbp_trading_sales_orders ADD CONSTRAINT chk_trd_so_total CHECK (total >= 0)",
    "ALTER TABLE dbp_trading_purchase_orders ADD CONSTRAINT chk_trd_po_total CHECK (total >= 0)",
    "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT chk_trd_si_total CHECK (total >= 0)",
    "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT chk_trd_si_paid CHECK (paid_amount >= 0)",
    "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT chk_trd_pi_total CHECK (total >= 0)",
    # NOT NULL on critical columns (tenant_id already handled by NOT NULL in CREATE)
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_trd_items_tenant ON dbp_trading_items(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_stock_tenant ON dbp_trading_stock(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_stock_item ON dbp_trading_stock(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_customers_tenant ON dbp_trading_customers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_suppliers_tenant ON dbp_trading_suppliers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_quotations_tenant ON dbp_trading_quotations(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_so_tenant ON dbp_trading_sales_orders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_so_customer ON dbp_trading_sales_orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_dn_tenant ON dbp_trading_delivery_notes(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_si_tenant ON dbp_trading_sales_invoices(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_si_customer ON dbp_trading_sales_invoices(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_cp_tenant ON dbp_trading_customer_payments(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_pr_tenant ON dbp_trading_purchase_requests(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_rfq_tenant ON dbp_trading_rfqs(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_sq_tenant ON dbp_trading_supplier_quotations(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_po_tenant ON dbp_trading_purchase_orders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_po_supplier ON dbp_trading_purchase_orders(supplier_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_grn_tenant ON dbp_trading_grn(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_pi_tenant ON dbp_trading_purchase_invoices(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_sp_tenant ON dbp_trading_supplier_payments(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_pl_tenant ON dbp_trading_price_lists(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_sr_tenant ON dbp_trading_sales_returns(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_preturn_tenant ON dbp_trading_purchase_returns(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_st_tenant ON dbp_trading_stock_transfers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_sa_tenant ON dbp_trading_stock_adjustments(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_trd_sm_tenant ON dbp_trading_salesmen(tenant_id)",
]

def run_migration():
    db = SessionLocal()
    created = 0
    skipped = 0
    errors = 0

    try:
        for ddl in TABLES:
            try:
                db.execute(text(ddl.strip()))
                created += 1
            except Exception as e:
                if "already exists" in str(e):
                    skipped += 1
                else:
                    print(f"  WARN: {str(e)[:80]}")
                    errors += 1

        db.commit()
        print(f"Tables: {created} created, {skipped} exist, {errors} errors")

        for stmt in CONSTRAINTS:
            try:
                db.execute(text(stmt))
            except Exception as e:
                if "already exists" in str(e) or "duplicate" in str(e):
                    pass
                else:
                    print(f"  WARN: {str(e)[:80]}")
        db.commit()

        for idx in INDEXES:
            try:
                db.execute(text(idx))
            except Exception as e:
                if "already exists" in str(e):
                    pass
                else:
                    print(f"  WARN: {str(e)[:80]}")
        db.commit()
        print("Constraints + Indexes applied")

        # Verify
        tables = db.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE 'dbp_trading_%' "
            "ORDER BY table_name"
        )).fetchall()
        print(f"\nTrading tables ({len(tables)}):")
        for t in tables:
            print(f"  {t[0]}")

    except Exception as e:
        db.rollback()
        print(f"FATAL: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
