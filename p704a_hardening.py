"""
P70.4A Trading Hardening Migration
====================================
Adds missing FK, UNIQUE, CHECK constraints, bilingual fields, and indexes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import engine, SessionLocal
from sqlalchemy import text

def run():
    db = SessionLocal()
    errors = 0
    applied = 0

    stmts = [
        # ═══════════════════════════════════════
        # MISSING FOREIGN KEYS (29 FKs)
        # ═══════════════════════════════════════
        "ALTER TABLE dbp_trading_quotations ADD CONSTRAINT fk_trd_q_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
        "ALTER TABLE dbp_trading_sales_orders ADD CONSTRAINT fk_trd_so_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
        "ALTER TABLE dbp_trading_sales_orders ADD CONSTRAINT fk_trd_so_quotation FOREIGN KEY (quotation_id) REFERENCES dbp_trading_quotations(id)",
        "ALTER TABLE dbp_trading_delivery_notes ADD CONSTRAINT fk_trd_dn_so FOREIGN KEY (so_id) REFERENCES dbp_trading_sales_orders(id)",
        "ALTER TABLE dbp_trading_delivery_notes ADD CONSTRAINT fk_trd_dn_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
        "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT fk_trd_si_dn FOREIGN KEY (dn_id) REFERENCES dbp_trading_delivery_notes(id)",
        "ALTER TABLE dbp_trading_customer_payments ADD CONSTRAINT fk_trd_cp_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
        "ALTER TABLE dbp_trading_rfqs ADD CONSTRAINT fk_trd_rfq_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_rfqs ADD CONSTRAINT fk_trd_rfq_pr FOREIGN KEY (pr_id) REFERENCES dbp_trading_purchase_requests(id)",
        "ALTER TABLE dbp_trading_supplier_quotations ADD CONSTRAINT fk_trd_sq_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_supplier_quotations ADD CONSTRAINT fk_trd_sq_rfq FOREIGN KEY (rfq_id) REFERENCES dbp_trading_rfqs(id)",
        "ALTER TABLE dbp_trading_purchase_orders ADD CONSTRAINT fk_trd_po_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_purchase_orders ADD CONSTRAINT fk_trd_po_sq FOREIGN KEY (sq_id) REFERENCES dbp_trading_supplier_quotations(id)",
        "ALTER TABLE dbp_trading_grn ADD CONSTRAINT fk_trd_grn_po FOREIGN KEY (po_id) REFERENCES dbp_trading_purchase_orders(id)",
        "ALTER TABLE dbp_trading_grn ADD CONSTRAINT fk_trd_grn_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT fk_trd_gl_po_line FOREIGN KEY (po_line_id) REFERENCES dbp_trading_purchase_order_lines(id)",
        "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT fk_trd_pi_grn FOREIGN KEY (grn_id) REFERENCES dbp_trading_grn(id)",
        "ALTER TABLE dbp_trading_supplier_payments ADD CONSTRAINT fk_trd_sp_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_sales_returns ADD CONSTRAINT fk_trd_sr_customer FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
        "ALTER TABLE dbp_trading_sales_returns ADD CONSTRAINT fk_trd_sr_invoice FOREIGN KEY (invoice_id) REFERENCES dbp_trading_sales_invoices(id)",
        "ALTER TABLE dbp_trading_sales_return_lines ADD CONSTRAINT fk_trd_srl_return FOREIGN KEY (return_id) REFERENCES dbp_trading_sales_returns(id)",
        "ALTER TABLE dbp_trading_sales_return_lines ADD CONSTRAINT fk_trd_srl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
        "ALTER TABLE dbp_trading_purchase_returns ADD CONSTRAINT fk_trd_pret_supplier FOREIGN KEY (supplier_id) REFERENCES dbp_trading_suppliers(id)",
        "ALTER TABLE dbp_trading_purchase_returns ADD CONSTRAINT fk_trd_pret_invoice FOREIGN KEY (invoice_id) REFERENCES dbp_trading_purchase_invoices(id)",
        "ALTER TABLE dbp_trading_purchase_return_lines ADD CONSTRAINT fk_trd_pretl_return FOREIGN KEY (return_id) REFERENCES dbp_trading_purchase_returns(id)",
        "ALTER TABLE dbp_trading_purchase_return_lines ADD CONSTRAINT fk_trd_pretl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
        "ALTER TABLE dbp_trading_stock_transfers ADD CONSTRAINT fk_trd_st_from FOREIGN KEY (from_warehouse_id) REFERENCES dbp_trading_warehouses(id)",
        "ALTER TABLE dbp_trading_stock_transfers ADD CONSTRAINT fk_trd_st_to FOREIGN KEY (to_warehouse_id) REFERENCES dbp_trading_warehouses(id)",
        "ALTER TABLE dbp_trading_stock_transfer_lines ADD CONSTRAINT fk_trd_stl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
        "ALTER TABLE dbp_trading_stock_adjustments ADD CONSTRAINT fk_trd_sa_warehouse FOREIGN KEY (warehouse_id) REFERENCES dbp_trading_warehouses(id)",
        "ALTER TABLE dbp_trading_stock_adjustment_lines ADD CONSTRAINT fk_trd_sal_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",
        "ALTER TABLE dbp_trading_territories ADD CONSTRAINT fk_trd_territory_parent FOREIGN KEY (parent_id) REFERENCES dbp_trading_territories(id)",

        # ═══════════════════════════════════════
        # MISSING UNIQUE CONSTRAINTS
        # ═══════════════════════════════════════
        "ALTER TABLE dbp_trading_price_lists ADD CONSTRAINT uq_trd_pl_tenant_name UNIQUE (tenant_id, list_name)",
        "ALTER TABLE dbp_trading_territories ADD CONSTRAINT uq_trd_territory_tenant_name UNIQUE (tenant_id, name)",

        # ═══════════════════════════════════════
        # MISSING CHECK CONSTRAINTS
        # ═══════════════════════════════════════
        "ALTER TABLE dbp_trading_stock ADD CONSTRAINT chk_trd_stock_intransit CHECK (in_transit >= 0)",
        "ALTER TABLE dbp_trading_stock ADD CONSTRAINT chk_trd_stock_unitcost CHECK (unit_cost >= 0)",
        "ALTER TABLE dbp_trading_delivery_lines ADD CONSTRAINT chk_trd_dl_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT chk_trd_gl_qr CHECK (qty_received >= 0)",
        "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT chk_trd_gl_qa CHECK (qty_accepted >= 0)",
        "ALTER TABLE dbp_trading_grn_lines ADD CONSTRAINT chk_trd_gl_qrj CHECK (qty_rejected >= 0)",
        "ALTER TABLE dbp_trading_customer_payments ADD CONSTRAINT chk_trd_cp_amount CHECK (amount > 0)",
        "ALTER TABLE dbp_trading_supplier_payments ADD CONSTRAINT chk_trd_sp_amount CHECK (amount > 0)",
        "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT chk_trd_pi_paid CHECK (paid_amount >= 0)",
        "ALTER TABLE dbp_trading_purchase_invoices ADD CONSTRAINT chk_trd_pi_balance CHECK (balance >= 0)",
        "ALTER TABLE dbp_trading_sales_invoices ADD CONSTRAINT chk_trd_si_balance CHECK (balance >= 0)",
        "ALTER TABLE dbp_trading_quotation_lines ADD CONSTRAINT chk_trd_ql_discount CHECK (discount_pct >= 0 AND discount_pct <= 100)",
        "ALTER TABLE dbp_trading_sales_order_lines ADD CONSTRAINT chk_trd_sol_delivered CHECK (delivered_qty >= 0)",
        "ALTER TABLE dbp_trading_purchase_order_lines ADD CONSTRAINT chk_trd_pol_received CHECK (received_qty >= 0)",
        "ALTER TABLE dbp_trading_quotation_lines ADD CONSTRAINT chk_trd_ql_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_sales_order_lines ADD CONSTRAINT chk_trd_sol_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_purchase_order_lines ADD CONSTRAINT chk_trd_pol_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_purchase_request_lines ADD CONSTRAINT chk_trd_prl_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_sales_return_lines ADD CONSTRAINT chk_trd_srl_qty CHECK (qty > 0)",
        "ALTER TABLE dbp_trading_purchase_return_lines ADD CONSTRAINT chk_trd_pretl_qty CHECK (qty > 0)",

        # ═══════════════════════════════════════
        # BILINGUAL FIELDS
        # ═══════════════════════════════════════
        "ALTER TABLE dbp_trading_salesmen ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200)",
        "ALTER TABLE dbp_trading_price_lists ADD COLUMN IF NOT EXISTS description_ar TEXT",
        "ALTER TABLE dbp_trading_quotations ADD COLUMN IF NOT EXISTS notes_ar TEXT",
        "ALTER TABLE dbp_trading_sales_orders ADD COLUMN IF NOT EXISTS notes_ar TEXT",
        "ALTER TABLE dbp_trading_purchase_orders ADD COLUMN IF NOT EXISTS notes_ar TEXT",
        "ALTER TABLE dbp_trading_delivery_notes ADD COLUMN IF NOT EXISTS notes_ar TEXT",

        # ═══════════════════════════════════════
        # UPDATED_AT TRIGGERS
        # ═══════════════════════════════════════
        """CREATE OR REPLACE FUNCTION update_trading_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql""",

        "DROP TRIGGER IF EXISTS trg_trd_items_updated ON dbp_trading_items",
        "CREATE TRIGGER trg_trd_items_updated BEFORE UPDATE ON dbp_trading_items FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_customers_updated ON dbp_trading_customers",
        "CREATE TRIGGER trg_trd_customers_updated BEFORE UPDATE ON dbp_trading_customers FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_suppliers_updated ON dbp_trading_suppliers",
        "CREATE TRIGGER trg_trd_suppliers_updated BEFORE UPDATE ON dbp_trading_suppliers FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_so_updated ON dbp_trading_sales_orders",
        "CREATE TRIGGER trg_trd_so_updated BEFORE UPDATE ON dbp_trading_sales_orders FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_po_updated ON dbp_trading_purchase_orders",
        "CREATE TRIGGER trg_trd_po_updated BEFORE UPDATE ON dbp_trading_purchase_orders FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_quot_updated ON dbp_trading_quotations",
        "CREATE TRIGGER trg_trd_quot_updated BEFORE UPDATE ON dbp_trading_quotations FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        "DROP TRIGGER IF EXISTS trg_trd_stock_updated ON dbp_trading_stock",
        "CREATE TRIGGER trg_trd_stock_updated BEFORE UPDATE ON dbp_trading_stock FOR EACH ROW EXECUTE FUNCTION update_trading_modified_column()",

        # ═══════════════════════════════════════
        # MISSING INDEXES
        # ═══════════════════════════════════════
        "CREATE INDEX IF NOT EXISTS idx_trd_qt_customer ON dbp_trading_quotations(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_dn_so ON dbp_trading_delivery_notes(so_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_cp_invoice ON dbp_trading_customer_payments(invoice_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_grn_po ON dbp_trading_grn(po_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_pi_grn ON dbp_trading_purchase_invoices(grn_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_sp_invoice ON dbp_trading_supplier_payments(invoice_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_sr_customer ON dbp_trading_sales_returns(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_pret_supplier ON dbp_trading_purchase_returns(supplier_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_st_from ON dbp_trading_stock_transfers(from_warehouse_id)",
        "CREATE INDEX IF NOT EXISTS idx_trd_st_to ON dbp_trading_stock_transfers(to_warehouse_id)",
    ]

    for stmt in stmts:
        try:
            db.execute(text(stmt))
            db.commit()
            applied += 1
        except Exception as e:
            db.rollback()
            if "already exists" in str(e) or "duplicate" in str(e) or "does not exist" in str(e) or "foreign key" in str(e):
                pass
            else:
                print(f"  WARN: {str(e)[:100]}")
                errors += 1

    db.commit()
    print(f"Applied: {applied}, Errors: {errors}")

    # Verify constraints
    fk_count = db.execute(text(
        "SELECT COUNT(*) FROM pg_constraint WHERE conrelid IN "
        "(SELECT oid FROM pg_class WHERE relname LIKE 'dbp_trading_%') AND contype='f'"
    )).fetchone()[0]
    uq_count = db.execute(text(
        "SELECT COUNT(*) FROM pg_constraint WHERE conrelid IN "
        "(SELECT oid FROM pg_class WHERE relname LIKE 'dbp_trading_%') AND contype='u'"
    )).fetchone()[0]
    ck_count = db.execute(text(
        "SELECT COUNT(*) FROM pg_constraint WHERE conrelid IN "
        "(SELECT oid FROM pg_class WHERE relname LIKE 'dbp_trading_%') AND contype='c'"
    )).fetchone()[0]
    idx_count = db.execute(text(
        "SELECT COUNT(*) FROM pg_indexes WHERE tablename LIKE 'dbp_trading_%'"
    )).fetchone()[0]

    print(f"\nConstraints: {fk_count} FK, {uq_count} UNIQUE, {ck_count} CHECK")
    print(f"Indexes: {idx_count}")

    db.close()

if __name__ == "__main__":
    run()
