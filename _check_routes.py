from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    for tbl in ['products', 'suppliers', 'warehouses', 'stock_movements', 'dbp_stock',
                'dbp_accounts', 'dbp_journal_entries', 'dbp_journal_lines',
                'dbp_projects', 'dbp_project_tasks', 'dbp_employees', 'dbp_departments',
                'dbp_sales_invoices', 'dbp_sales_invoice_lines',
                'dbp_sales_orders', 'dbp_sales_order_lines']:
        r = db.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{tbl}' ORDER BY ordinal_position"
        ))
        cols = [row[0] for row in r]
        print(f"{tbl}: {', '.join(cols[:15])}")
        print()
finally:
    db.close()
