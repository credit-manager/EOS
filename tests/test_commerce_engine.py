import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Direct DB access for testing
DATABASE_URL = "postgresql://eos:0100@127.0.0.1:5432/eos_main"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Import Commerce Engine
sys.path.insert(0, r"D:\EOS\Eos final")
from core.commerce_engine import (
    atomic_stock_issue,
    atomic_stock_receive,
    commerce_dashboard,
    create_customer,
    create_item,
    create_price_list,
    create_supplier,
    create_warehouse,
    get_customer,
    get_item,
    get_item_by_barcode,
    get_stock,
    get_supplier,
    get_warehouse,
    list_customers,
    list_items,
    list_price_lists,
    list_stock,
    list_suppliers,
    list_warehouses,
    update_customer,
    update_item,
    update_supplier,
)

# Get demo tenant
db = Session()
row = db.execute(text("SELECT id FROM tenants LIMIT 1")).fetchone()
TENANT_A = row[0]
TENANT_B = str(uuid.uuid4())  # fake second tenant for isolation test
USER_ID = "00000000-0000-0000-0000-000000000001"
passed = 0
failed = 0
total = 0
_rid = uuid.uuid4().hex[:6].upper()


def test(name, cond):
    global passed, failed, total
    total += 1
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


# ═══════════════════════════════════════
print("=== Commerce Engine C.1 Tests ===\n")

# ═══ ITEMS ═══
print("--- Items ---")
item = create_item(db, TENANT_A, {
    "item_code": f"CE-{_rid}-1", "name": f"Widget-{_rid}",
    "category": "hardware", "unit": "piece",
    "cost_price": 10.50, "selling_price": 25.00,
    "min_stock": 5, "max_stock": 500, "reorder_point": 10,
    "barcode": f"BC-{_rid}-1",
}, user_id=USER_ID)
test("Create item", item["id"] is not None and item["item_code"] == f"CE-{_rid}-1")
test("Item has float prices", isinstance(item["cost_price"], float) and item["cost_price"] == 10.5)

item2 = create_item(db, TENANT_A, {
    "item_code": f"CE-{_rid}-2", "name": f"Gadget-{_rid}",
    "category": "electronics", "unit": "piece",
    "cost_price": 5.00, "selling_price": 15.00,
    "barcode": f"BC-{_rid}-2",
}, user_id=USER_ID)
test("Create second item", item2["id"] is not None)

got = get_item(db, TENANT_A, item["id"])
test("Get item by ID", got["name"] == f"Widget-{_rid}")

got_barcode = get_item_by_barcode(db, TENANT_A, f"BC-{_rid}-1")
test("Get item by barcode", got_barcode["id"] == item["id"])

updated = update_item(db, TENANT_A, item["id"], {
    "selling_price": 30.00, "name": f"Widget-{_rid}-v2",
}, user_id=USER_ID)
test("Update item price", updated["selling_price"] == 30.00 and updated["name"].endswith("-v2"))

items_list = list_items(db, TENANT_A, search=_rid)
test("List items", items_list["total"] >= 2 and len(items_list["data"]) >= 2)

# Duplicate code
try:
    create_item(db, TENANT_A, {"item_code": f"CE-{_rid}-1", "name": "Dup"})
    test("Duplicate item_code rejected", False)
except Exception:
    test("Duplicate item_code rejected", True)

# Missing fields
try:
    create_item(db, TENANT_A, {"name": "No Code"})
    test("Missing item_code rejected", False)
except Exception:
    test("Missing item_code rejected", True)

# Negative price
try:
    create_item(db, TENANT_A, {"item_code": "NEG", "name": "Neg", "cost_price": -5})
    test("Negative cost_price rejected", False)
except Exception:
    test("Negative cost_price rejected", True)


# ═══ WAREHOUSES ═══
print("\n--- Warehouses ---")
wh = create_warehouse(db, TENANT_A, {
    "code": f"WH-{_rid}", "name": f"Warehouse-{_rid}",
    "address": "Riyadh", "manager": "Ahmed",
}, user_id=USER_ID)
test("Create warehouse", wh["id"] is not None and wh["code"] == f"WH-{_rid}")

wh2 = create_warehouse(db, TENANT_A, {
    "code": f"WH2-{_rid}", "name": f"Warehouse2-{_rid}",
}, user_id=USER_ID)
test("Create second warehouse", wh2["id"] is not None)

whs = list_warehouses(db, TENANT_A)
test("List warehouses", len(whs) >= 2)

got_wh = get_warehouse(db, TENANT_A, wh["id"])
test("Get warehouse", got_wh["code"] == f"WH-{_rid}")

# Duplicate code
try:
    create_warehouse(db, TENANT_A, {"code": f"WH-{_rid}", "name": "Dup"})
    test("Duplicate warehouse code rejected", False)
except Exception:
    test("Duplicate warehouse code rejected", True)


# ═══ CUSTOMERS ═══
print("\n--- Customers ---")
cust = create_customer(db, TENANT_A, {
    "customer_code": f"CUST-{_rid}", "name": f"Customer-{_rid}",
    "email": f"cust-{_rid}@test.com", "phone": "+966500000",
    "credit_limit": 10000,
}, user_id=USER_ID)
test("Create customer", cust["id"] is not None and cust["credit_limit"] == 10000)

cust2 = create_customer(db, TENANT_A, {
    "customer_code": f"CUST2-{_rid}", "name": f"Customer2-{_rid}",
}, user_id=USER_ID)
test("Create second customer", cust2["id"] is not None)

custs = list_customers(db, TENANT_A, search=_rid)
test("List customers", custs["total"] >= 2)

got_cust = get_customer(db, TENANT_A, cust["id"])
test("Get customer", got_cust["name"] == f"Customer-{_rid}")

updated_cust = update_customer(db, TENANT_A, cust["id"], {
    "credit_limit": 20000, "phone": "+966511111",
}, user_id=USER_ID)
test("Update customer", updated_cust["credit_limit"] == 20000)

# Negative credit limit
try:
    create_customer(db, TENANT_A, {"customer_code": "NEG", "name": "Neg", "credit_limit": -100})
    test("Negative credit_limit rejected", False)
except Exception:
    test("Negative credit_limit rejected", True)


# ═══ SUPPLIERS ═══
print("\n--- Suppliers ---")
supp = create_supplier(db, TENANT_A, {
    "supplier_code": f"SUPP-{_rid}", "name": f"Supplier-{_rid}",
    "email": f"supp-{_rid}@test.com", "lead_time_days": 14,
}, user_id=USER_ID)
test("Create supplier", supp["id"] is not None and supp["lead_time_days"] == 14)

supp2 = create_supplier(db, TENANT_A, {
    "supplier_code": f"SUPP2-{_rid}", "name": f"Supplier2-{_rid}",
}, user_id=USER_ID)
test("Create second supplier", supp2["id"] is not None)

supps = list_suppliers(db, TENANT_A, search=_rid)
test("List suppliers", supps["total"] >= 2)

got_supp = get_supplier(db, TENANT_A, supp["id"])
test("Get supplier", got_supp["name"] == f"Supplier-{_rid}")

updated_supp = update_supplier(db, TENANT_A, supp["id"], {
    "lead_time_days": 21,
}, user_id=USER_ID)
test("Update supplier lead time", updated_supp["lead_time_days"] == 21)


# ═══ STOCK ═══
print("\n--- Stock Operations ---")
stock_id = atomic_stock_receive(db, TENANT_A, item["id"], qty=100, price=10.50,
                                 warehouse_id=wh["id"], user_id=USER_ID)
test("Stock receive (first)", stock_id is not None)

stk = get_stock(db, TENANT_A, item["id"], wh["id"])
test("Stock level after receive", stk["on_hand"] == 100)

stock_id2 = atomic_stock_receive(db, TENANT_A, item["id"], qty=50, price=12.00,
                                  warehouse_id=wh["id"], user_id=USER_ID)
test("Stock receive (second, weighted avg)", stock_id2 == stock_id)

stk2 = get_stock(db, TENANT_A, item["id"], wh["id"])
test("Stock level after 2nd receive", stk2["on_hand"] == 150)
# Weighted average: (100*10.5 + 50*12) / 150 = (1050+600)/150 = 11.0
test("Weighted avg cost", abs(stk2["unit_cost"] - 11.0) < 0.01)

issued = atomic_stock_issue(db, TENANT_A, item["id"], qty=30, warehouse_id=wh["id"], user_id=USER_ID)
test("Stock issue", issued[0] == stock_id)

stk3 = get_stock(db, TENANT_A, item["id"], wh["id"])
test("Stock level after issue", stk3["on_hand"] == 120)

# Insufficient stock
try:
    atomic_stock_issue(db, TENANT_A, item["id"], qty=999, warehouse_id=wh["id"])
    test("Insufficient stock rejected", False)
except Exception:
    test("Insufficient stock rejected", True)

# Negative qty
try:
    atomic_stock_receive(db, TENANT_A, item["id"], qty=-10, price=5, warehouse_id=wh["id"])
    test("Negative qty rejected", False)
except Exception:
    test("Negative qty rejected", True)

stock_list = list_stock(db, TENANT_A, search=_rid)
test("List stock", stock_list["total"] >= 1)


# ═══ PRICING ═══
print("\n--- Pricing ---")
pl = create_price_list(db, TENANT_A, {"name": f"PriceList-{_rid}", "currency": "SAR"}, user_id=USER_ID)
test("Create price list", pl["id"] is not None)

pls = list_price_lists(db, TENANT_A)
test("List price lists", len(pls) >= 1)


# ═══ DASHBOARD ═══
print("\n--- Dashboard ---")
dash = commerce_dashboard(db, TENANT_A)
test("Dashboard items", dash["items"] >= 2)
test("Dashboard customers", dash["customers"] >= 2)
test("Dashboard suppliers", dash["suppliers"] >= 2)
test("Dashboard warehouses", dash["warehouses"] >= 2)
test("Dashboard stock_value", dash["stock_value"] > 0)


# ═══ TENANT ISOLATION ═══
print("\n--- Tenant Isolation ---")
try:
    get_item(db, TENANT_B, item["id"])
    test("Cross-tenant item access blocked", False)
except Exception:
    test("Cross-tenant item access blocked", True)

items_b = list_items(db, TENANT_B)
test("Cross-tenant item listing empty", items_b["total"] == 0)

custs_b = list_customers(db, TENANT_B)
test("Cross-tenant customer listing empty", custs_b["total"] == 0)


# ═══ FULL LIFECYCLE ═══
print("\n--- Full Lifecycle ---")
# Create item → receive stock → issue stock → check audit
lc_item = create_item(db, TENANT_A, {
    "item_code": f"LC-{_rid}", "name": f"Lifecycle-{_rid}",
    "cost_price": 20, "selling_price": 50, "unit": "kg",
}, user_id=USER_ID)
lc_wh = create_warehouse(db, TENANT_A, {"code": f"LCWH-{_rid}", "name": f"LC-WH-{_rid}"}, user_id=USER_ID)

sid1 = atomic_stock_receive(db, TENANT_A, lc_item["id"], 200, 20, lc_wh["id"], user_id=USER_ID)
sid2 = atomic_stock_issue(db, TENANT_A, lc_item["id"], 75, lc_wh["id"], user_id=USER_ID)
lc_stock = get_stock(db, TENANT_A, lc_item["id"], lc_wh["id"])

test("Lifecycle: receive 200", sid1 is not None)
test("Lifecycle: issue 75", sid2[1] == 20.0)
test("Lifecycle: remaining 125", lc_stock["on_hand"] == 125)

# Check audit records
audit_count = db.execute(text(
    "SELECT COUNT(*) FROM dbp_construction_audit "
    "WHERE entity_type LIKE 'commerce_%' AND tenant_id=:t"
), {"t": TENANT_A}).fetchone()[0]
test("Lifecycle: audit recorded", audit_count > 0)


# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"Commerce Engine C.1 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")

db.close()
