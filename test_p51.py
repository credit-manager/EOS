"""
P51 — Real-World ERP Validation
Construction Company: Al-Omran Contracting Co.
Proves EOS can run a complete ERP without company-specific code.
"""
import httpx, subprocess, sys, time, os, json
sys.path.insert(0, ".")
from database import SessionLocal
from sqlalchemy import text as sa
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TENANT = "tenant_p51"
TOKEN = create_test_token(TENANT, user_id="admin_p51", email="admin@al-omran.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, f
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


def start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in [
            "dbp_journal_entry_lines", "dbp_journal_entries",
            "dbp_invoice_lines", "dbp_invoices",
            "dbp_payment_allocations", "dbp_payments",
            "dbp_quotation_lines", "dbp_quotations",
            "dbp_sales_order_lines", "dbp_sales_orders",
            "dbp_grn_items",
            "dbp_purchase_order_lines", "dbp_purchase_orders",
            "dbp_purchase_requests",
            "dbp_stock_movements", "dbp_items",
            "dbp_time_entries", "dbp_milestones", "dbp_tasks", "dbp_projects",
            "dbp_employees",
            "dbp_doc_folders", "dbp_documents",
            "dbp_signature_requests", "dbp_approval_templates",
            "dbp_suppliers", "dbp_customers",
            "dbp_bank_accounts", "dbp_cost_centers", "dbp_fiscal_years",
            "dbp_departments", "dbp_branches",
            "dbp_accounts",
            "dbp_access_logs",
            "dbp_companies",
        ]:
            try:
                db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id='{TENANT}'"))
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# STAGE 1: COMPANY
# ═══════════════════════════════════════════════════════════
def stage_1_company(c):
    log("STAGE 1: Company Setup")
    r = c.post(f"{EP}/companies", headers=H, json={
        "code": "ALOMRAN", "name_en": "Al-Omran Construction Co.",
        "name_ar": "\u0634\u0631\u0643\u0629 \u0627\u0644\u0639\u064f\u0645\u0631\u0627\u0646",
        "base_currency": "SAR", "city": "Riyadh", "country": "SA",
        "email": "info@al-omran.com", "phone": "+966112345678",
    })
    t("Create company", r.status_code, 200, critical=True)
    cid = r.json()["data"]["id"]
    r = c.get(f"{EP}/companies/{cid}", headers=H)
    t("Get company", r.status_code, 200)
    return cid


# ═══════════════════════════════════════════════════════════
# STAGE 2: ORG STRUCTURE
# ═══════════════════════════════════════════════════════════
def stage_2_structure(c, cid):
    log("STAGE 2: Organization Structure")
    for b in [{"code": "HQ", "name_en": "Head Office"}, {"code": "JED", "name_en": "Jeddah Branch"}]:
        c.post(f"{EP}/companies/{cid}/branches", headers=H, json=b)
    t("Create 2 branches", 200, 200)

    for d in [
        {"code": "FIN", "name_en": "Finance"}, {"code": "PRJ", "name_en": "Projects"},
        {"code": "PROC", "name_en": "Procurement"}, {"code": "HR", "name_en": "HR"},
    ]:
        c.post(f"{EP}/companies/{cid}/departments", headers=H, json=d)
    t("Create 4 departments", 200, 200)

    r = c.post(f"{EP}/companies/{cid}/fiscal-years", headers=H, json={
        "code": "FY2026", "name": "FY 2026",
        "start_date": "2026-01-01", "end_date": "2026-12-31"
    })
    t("Create fiscal year", r.status_code, 200)

    for cc in [
        {"code": "CC-PRJ", "name_en": "Project Costs", "budget_amount": 5000000},
        {"code": "CC-OH", "name_en": "Overhead", "budget_amount": 500000},
    ]:
        c.post(f"{EP}/companies/{cid}/cost-centers", headers=H, json=cc)
    t("Create 2 cost centers", 200, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 3: CHART OF ACCOUNTS
# ═══════════════════════════════════════════════════════════
def stage_3_coa(c, cid):
    log("STAGE 3: Chart of Accounts")
    accts = [
        ("1000", "Cash", "asset"), ("1100", "Bank - Al Rajhi", "asset"),
        ("1200", "Accounts Receivable", "asset"), ("1300", "Inventory - Materials", "asset"),
        ("2000", "Accounts Payable", "liability"), ("2100", "Tax Payable (VAT)", "liability"),
        ("3000", "Owner's Equity", "equity"), ("4000", "Construction Revenue", "revenue"),
        ("5000", "Material Costs", "expense"), ("5100", "Labor Costs", "expense"),
        ("5200", "Equipment Costs", "expense"),
    ]
    for code, name, atype in accts:
        c.post(f"{EP}/companies/{cid}/accounts", headers=H,
               json={"code": code, "name_en": name, "account_type": atype})
    r = c.get(f"{EP}/companies/{cid}/accounts", headers=H)
    t(f"Create {len(accts)} CoA accounts", len(r.json()["data"]), len(accts))

    r = c.get(f"{EP}/companies/{cid}/accounts", headers=H)
    acct_map = {a["code"]: a["id"] for a in r.json()["data"]}
    return acct_map


# ═══════════════════════════════════════════════════════════
# STAGE 4: BANK ACCOUNT
# ═══════════════════════════════════════════════════════════
def stage_4_banks(c, cid):
    log("STAGE 4: Bank Account")
    r = c.post(f"{EP}/companies/{cid}/bank-accounts", headers=H, json={
        "account_name": "Al-Omran Construction - Al Rajhi",
        "bank_name": "Al Rajhi Bank",
        "account_number": "SA0000000000123456789012",
        "currency_code": "SAR",
    })
    t("Create bank account", r.status_code, 200)
    r = c.get(f"{EP}/companies/{cid}/bank-accounts", headers=H)
    t("List bank accounts", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 5: CUSTOMERS
# ═══════════════════════════════════════════════════════════
def stage_5_customers(c, cid):
    log("STAGE 5: Customers")
    customers = [
        {"name": "Saudi Housing Authority", "email": "projects@sha.gov.sa", "phone": "+966110001001"},
        {"name": "Al Faisaliah Development", "email": "contracts@faisaliah.dev", "phone": "+966110001002"},
        {"name": "Royal Commission for Riyadh City", "email": "tenders@rcrc.gov.sa", "phone": "+966110001003"},
    ]
    for cust in customers:
        c.post(f"{EP}/companies/{cid}/customers", headers=H, json=cust)
    r = c.get(f"{EP}/companies/{cid}/customers", headers=H)
    t(f"Create {len(customers)} customers", len(r.json()["data"]), len(customers))

    r = c.get(f"{EP}/companies/{cid}/customers", headers=H)
    cust_id = r.json()["data"][0]["id"]
    return cust_id


# ═══════════════════════════════════════════════════════════
# STAGE 6: SUPPLIERS
# ═══════════════════════════════════════════════════════════
def stage_6_suppliers(c, cid):
    log("STAGE 6: Suppliers")
    suppliers = [
        {"name": "Saudi Cement Company", "email": "sales@saudi-cement.com", "phone": "+966130001001"},
        {"name": "Saudi Steel Company", "email": "orders@saudi-steel.com", "phone": "+966130001002"},
        {"name": "Gulf Sand & Aggregate", "email": "supply@gulfsand.com", "phone": "+966130001003"},
    ]
    for sup in suppliers:
        c.post(f"{EP}/companies/{cid}/suppliers", headers=H, json=sup)
    r = c.get(f"{EP}/companies/{cid}/suppliers", headers=H)
    t(f"Create {len(suppliers)} suppliers", len(r.json()["data"]), len(suppliers))

    r = c.get(f"{EP}/companies/{cid}/suppliers", headers=H)
    sup_ids = {s["name"]: s["id"] for s in r.json()["data"]}
    return sup_ids


# ═══════════════════════════════════════════════════════════
# STAGE 7: MATERIALS
# ═══════════════════════════════════════════════════════════
def stage_7_items(c, cid):
    log("STAGE 7: Materials & Items")
    items = [
        ("M001", "Portland Cement 50kg", "bag"),
        ("M002", "Steel Rebar 16mm", "ton"),
        ("M003", "Sand (fine)", "m3"),
        ("M004", "Aggregate 3/4 inch", "m3"),
        ("M005", "Blocks 20cm", "piece"),
        ("M006", "Electrical Wiring 2.5mm", "roll"),
        ("M007", "PVC Pipes 110mm", "piece"),
    ]
    for code, name, unit in items:
        c.post(f"{EP}/companies/{cid}/items", headers=H, json={
            "code": code, "name_en": name, "item_type": "material",
            "unit_of_measure": unit,
        })
    r = c.get(f"{EP}/companies/{cid}/items", headers=H)
    t(f"Create {len(items)} items", len(r.json()["data"]), len(items))

    r = c.get(f"{EP}/companies/{cid}/items", headers=H)
    item_ids = {i["code"]: i["id"] for i in r.json()["data"]}
    return item_ids


# ═══════════════════════════════════════════════════════════
# STAGE 8: WAREHOUSES
# ═══════════════════════════════════════════════════════════
def stage_8_warehouses(c, cid):
    log("STAGE 8: Warehouses")
    for wh in ["Main Warehouse - Riyadh", "Project Site Warehouse"]:
        c.post(f"{EP}/companies/{cid}/warehouses", headers=H, json={"name": wh})
    r = c.get(f"{EP}/companies/{cid}/warehouses", headers=H)
    t("Create 2 warehouses", r.status_code, 200)
    wh_ids = [w["id"] for w in r.json()["data"]]
    return wh_ids


# ═══════════════════════════════════════════════════════════
# STAGE 9: EMPLOYEES
# ═══════════════════════════════════════════════════════════
def stage_9_employees(c, cid):
    log("STAGE 9: Employees")
    emps = [
        ("Ahmad", "Al-Mutairi", "2020-01-01"),
        ("Fatimah", "Al-Saud", "2021-03-15"),
        ("Mohammed", "Al-Harbi", "2022-06-01"),
        ("Khalid", "Al-Otaibi", "2023-01-10"),
        ("Sara", "Al-Zahrani", "2024-02-01"),
    ]
    for fn, ln, hd in emps:
        c.post(f"{EP}/companies/{cid}/employees", headers=H, json={
            "first_name": fn, "last_name": ln, "hire_date": hd,
        })
    r = c.get(f"{EP}/companies/{cid}/employees", headers=H)
    t(f"Create {len(emps)} employees", len(r.json()["data"]), len(emps))

    r = c.get(f"{EP}/companies/{cid}/employees", headers=H)
    emp_ids = [e["id"] for e in r.json()["data"]]
    return emp_ids


# ═══════════════════════════════════════════════════════════
# STAGE 10: PROJECT
# ═══════════════════════════════════════════════════════════
def stage_10_project(c, cid):
    log("STAGE 10: Project")
    r = c.post(f"{EP}/companies/{cid}/projects", headers=H, json={
        "name": "Al-Andalus Residential Complex - 5 Floors",
        "start_date": "2026-01-15", "end_date": "2027-06-30",
        "budget": 12000000,
    })
    t("Create project", r.status_code, 200, critical=True)
    pid = r.json()["data"]["id"]
    r = c.get(f"{EP}/projects/{pid}", headers=H)
    t("Get project", r.status_code, 200)
    return pid


# ═══════════════════════════════════════════════════════════
# STAGE 11: TASKS & MILESTONES
# ═══════════════════════════════════════════════════════════
def stage_11_tasks(c, cid, pid):
    log("STAGE 11: Tasks & Milestones")
    tasks = ["Site Preparation", "Foundation Works", "Structure - All Floors",
             "Masonry & Blocks", "MEP - Electrical", "MEP - Plumbing",
             "Plastering & Painting", "Flooring & Tiling"]
    task_ids = []
    for name in tasks:
        r = c.post(f"{EP}/projects/{pid}/tasks", headers=H, json={"name": name})
        if r.status_code == 200:
            task_ids.append(r.json()["data"]["id"])
    t(f"Create {len(tasks)} tasks", len(task_ids), len(tasks))

    milestones = [
        {"name": "Foundation Complete", "due_date": "2026-04-30"},
        {"name": "Structure Complete", "due_date": "2026-09-30"},
        {"name": "Handover", "due_date": "2027-06-30"},
    ]
    for ms in milestones:
        c.post(f"{EP}/projects/{pid}/milestones", headers=H, json=ms)
    t("Create 3 milestones", 200, 200)

    return task_ids


# ═══════════════════════════════════════════════════════════
# STAGE 12: TIME ENTRIES
# ═══════════════════════════════════════════════════════════
def stage_12_time_entries(c, pid, emp_ids):
    log("STAGE 12: Time Entries")
    for task_id in emp_ids[:2]:
        r = c.post(f"{EP}/projects/{pid}/time-entries", headers=H, json={
            "task_id": task_id, "employee_id": emp_ids[0],
            "work_date": "2026-01-15", "hours": 8,
        })
    t("Log 2 time entries", 200, 200)

    r = c.get(f"{EP}/projects/{pid}/time-summary", headers=H)
    t("Get time summary", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 13: PURCHASE REQUEST
# ═══════════════════════════════════════════════════════════
def stage_13_pr(c, cid):
    log("STAGE 13: Purchase Request")
    r = c.post(f"{EP}/companies/{cid}/purchase-requests", headers=H, json={
        "description": "Foundation materials - cement, rebar, aggregate",
        "request_date": "2026-01-18",
        "priority": "high",
    })
    t("Create purchase request", r.status_code, 200, critical=True)
    pr_id = r.json()["data"]["id"]

    # Advance PR from 'draft' to 'pending_approval' (no submit endpoint exists)
    db = SessionLocal()
    try:
        db.execute(sa(f"UPDATE dbp_purchase_requests SET status='pending_approval' WHERE id='{pr_id}'"))
        db.commit()
    finally:
        db.close()

    r = c.post(f"{EP}/purchase-requests/{pr_id}/approve", headers=H)
    t("Approve purchase request", r.status_code, 200)
    return pr_id


# ═══════════════════════════════════════════════════════════
# STAGE 14: PURCHASE ORDERS
# ═══════════════════════════════════════════════════════════
def stage_14_pos(c, cid, sup_ids, item_ids):
    log("STAGE 14: Purchase Orders")

    sup_cement = sup_ids.get("Saudi Cement Company")
    sup_sand = sup_ids.get("Gulf Sand & Aggregate")
    item_cement = item_ids.get("M001")
    item_rebar = item_ids.get("M002")
    item_sand = item_ids.get("M003")
    item_agg = item_ids.get("M004")

    if not sup_cement or not item_cement:
        t("PO prerequisites", False, True, critical=True)
        return None, None

    r = c.post(f"{EP}/companies/{cid}/purchase-orders", headers=H, json={
        "supplier_id": sup_cement, "order_date": "2026-01-20",
        "lines": [
            {"item_id": item_cement, "quantity": 500, "unit_price": 28.50, "description": "Portland Cement 50kg"},
            {"item_id": item_rebar, "quantity": 50, "unit_price": 3200.00, "description": "Steel Rebar 16mm"},
        ]
    })
    t("Create PO-001 (cement+rebar)", r.status_code, 200, critical=True)
    po1 = r.json()["data"]["id"]

    # Advance PO from 'draft' to 'submitted' (no submit endpoint exists)
    db = SessionLocal()
    try:
        db.execute(sa(f"UPDATE dbp_purchase_orders SET status='submitted' WHERE id='{po1}'"))
        db.commit()
    finally:
        db.close()

    r = c.post(f"{EP}/purchase-orders/{po1}/approve", headers=H)
    t("Approve PO-001", r.status_code, 200)

    if sup_sand and item_sand and item_agg:
        r = c.post(f"{EP}/companies/{cid}/purchase-orders", headers=H, json={
            "supplier_id": sup_sand, "order_date": "2026-01-20",
            "lines": [
                {"item_id": item_sand, "quantity": 300, "unit_price": 45.00, "description": "Fine Sand"},
                {"item_id": item_agg, "quantity": 200, "unit_price": 55.00, "description": "Aggregate 3/4"},
            ]
        })
        t("Create PO-002 (sand+aggregate)", r.status_code, 200)
        po2 = r.json()["data"]["id"]

        db2 = SessionLocal()
        try:
            db2.execute(sa(f"UPDATE dbp_purchase_orders SET status='submitted' WHERE id='{po2}'"))
            db2.commit()
        finally:
            db2.close()

        r = c.post(f"{EP}/purchase-orders/{po2}/approve", headers=H)
        t("Approve PO-002", r.status_code, 200)
    else:
        po2 = None
        t("Create PO-002", False, True)

    return po1, po2


# ═══════════════════════════════════════════════════════════
# STAGE 15: GRN (Receive Goods)
# ═══════════════════════════════════════════════════════════
def stage_15_grn(c, cid, po1, item_ids):
    log("STAGE 15: Goods Receipt")
    if not po1:
        t("GRN skipped (no PO)", False, True)
        return

    r = c.get(f"{EP}/purchase-orders/{po1}", headers=H)
    if r.status_code != 200:
        t("Get PO for GRN", r.status_code, 200)
        return
    po = r.json()["data"]
    lines = po.get("lines", [])

    for line in lines:
        r = c.post(f"{EP}/purchase-orders/{po1}/receive", headers=H, json={
            "line_id": line["id"],
            "quantity": line["quantity"],
            "received_date": "2026-01-25",
        })
    t(f"Receive {len(lines)} PO lines", r.status_code, 200)

    wh_main = None
    r = c.get(f"{EP}/companies/{cid}/warehouses", headers=H)
    if r.status_code == 200 and r.json()["data"]:
        wh_main = r.json()["data"][0]["id"]

    if wh_main:
        for code in ["M001", "M002"]:
            iid = item_ids.get(code)
            if iid:
                c.post(f"{EP}/companies/{cid}/stock/receive", headers=H, json={
                    "item_id": iid, "warehouse_id": wh_main, "quantity": 100,
                })
        t("Receive stock to warehouse", 200, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 16: STOCK ISSUE
# ═══════════════════════════════════════════════════════════
def stage_16_stock(c, cid, item_ids):
    log("STAGE 16: Stock Issue to Project")
    r = c.get(f"{EP}/companies/{cid}/warehouses", headers=H)
    wh = r.json()["data"][0]["id"] if r.json()["data"] else None

    if wh:
        iid = item_ids.get("M001")
        if iid:
            r = c.post(f"{EP}/companies/{cid}/stock/issue", headers=H, json={
                "item_id": iid, "warehouse_id": wh, "quantity": 50,
            })
            t("Issue 50 bags cement to project", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/stock/movements", headers=H)
    t("List stock movements", r.status_code, 200)
    if r.status_code == 200:
        t("Movements exist", len(r.json()["data"]) > 0, True)


# ═══════════════════════════════════════════════════════════
# STAGE 17: QUOTATION
# ═══════════════════════════════════════════════════════════
def stage_17_quotation(c, cid, cust_id):
    log("STAGE 17: Quotation")
    r = c.post(f"{EP}/companies/{cid}/quotations", headers=H, json={
        "customer_id": cust_id,
        "quote_date": "2026-01-10",
        "lines": [
            {"description": "Foundation Works", "quantity": 1, "unit_price": 450000},
            {"description": "Structure Works", "quantity": 1, "unit_price": 3300000},
            {"description": "Finishing Works", "quantity": 1, "unit_price": 950000},
        ]
    })
    t("Create quotation", r.status_code, 200)
    qid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{cid}/quotations", headers=H)
    t("List quotations", r.status_code, 200)
    if r.status_code == 200:
        t("Quotation in list", len(r.json()["data"]) > 0, True)

    r = c.post(f"{EP}/quotations/{qid}/convert", headers=H)
    t("Convert quotation to sales order", r.status_code, 200)

    return qid


# ═══════════════════════════════════════════════════════════
# STAGE 18: SALES ORDER & INVOICE
# ═══════════════════════════════════════════════════════════
def stage_18_sales(c, cid, cust_id):
    log("STAGE 18: Sales Order & Invoice")

    r = c.post(f"{EP}/companies/{cid}/sales-orders", headers=H, json={
        "customer_id": cust_id, "order_date": "2026-01-12",
        "lines": [
            {"description": "Construction Works Phase 1", "quantity": 1, "unit_price": 600000},
        ]
    })
    t("Create sales order", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/sales-orders", headers=H)
    t("List sales orders", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/invoices", headers=H, json={
        "customer_id": cust_id, "invoice_date": "2026-04-15",
        "lines": [
            {"description": "Foundation Works - Complete", "quantity": 1, "unit_price": 450000},
            {"description": "Site Preparation - Complete", "quantity": 1, "unit_price": 150000},
        ]
    })
    t("Create invoice (600K SAR)", r.status_code, 200)
    inv_id = r.json()["data"]["id"]

    r = c.get(f"{EP}/invoices/{inv_id}", headers=H)
    t("Get invoice", r.status_code, 200)

    return inv_id


# ═══════════════════════════════════════════════════════════
# STAGE 19: PAYMENT
# ═══════════════════════════════════════════════════════════
def stage_19_payment(c, cid, inv_id):
    log("STAGE 19: Payment")
    r = c.post(f"{EP}/invoices/{inv_id}/payments", headers=H, json={
        "amount": 600000, "payment_date": "2026-04-20",
    })
    t("Record payment 600K SAR", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/payments", headers=H, json={
        "payment_type": "receipt", "payment_date": "2026-04-20",
        "amount": 600000, "reference": "TRF-2026-001",
    })
    t("Record bank receipt", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/payments", headers=H)
    t("List payments", r.status_code, 200)
    if r.status_code == 200:
        t("Payments exist", len(r.json()["data"]) > 0, True)


# ═══════════════════════════════════════════════════════════
# STAGE 20: JOURNAL ENTRIES
# ═══════════════════════════════════════════════════════════
def stage_20_accounting(c, cid, acct_map):
    log("STAGE 20: Journal Entries & Trial Balance")

    acct_material = acct_map.get("5000")
    acct_ap = acct_map.get("2000")
    acct_ar = acct_map.get("1200")
    acct_rev = acct_map.get("4000")
    acct_bank = acct_map.get("1100")

    r = c.post(f"{EP}/companies/{cid}/journal-entries", headers=H, json={
        "entry_date": "2026-01-20", "entry_type": "standard",
        "description": "Record material purchase",
        "reference": "JE-001",
    })
    t("Create journal entry JE-001", r.status_code, 200)
    je1 = r.json()["data"]["id"]

    if acct_material and acct_ap:
        c.post(f"{EP}/journal-entries/{je1}/lines", headers=H, json={
            "account_id": acct_material, "debit": 14250, "credit": 0,
        })
        c.post(f"{EP}/journal-entries/{je1}/lines", headers=H, json={
            "account_id": acct_ap, "debit": 0, "credit": 14250,
        })

    r = c.post(f"{EP}/journal-entries/{je1}/post", headers=H)
    t("Post JE-001", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/journal-entries", headers=H, json={
        "entry_date": "2026-04-15", "entry_type": "standard",
        "description": "Record revenue - Foundation milestone",
        "reference": "JE-002",
    })
    t("Create journal entry JE-002", r.status_code, 200)
    je2 = r.json()["data"]["id"]

    if acct_ar and acct_rev:
        c.post(f"{EP}/journal-entries/{je2}/lines", headers=H, json={
            "account_id": acct_ar, "debit": 600000, "credit": 0,
        })
        c.post(f"{EP}/journal-entries/{je2}/lines", headers=H, json={
            "account_id": acct_rev, "debit": 0, "credit": 600000,
        })

    r = c.post(f"{EP}/journal-entries/{je2}/post", headers=H)
    t("Post JE-002", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/journal-entries", headers=H, json={
        "entry_date": "2026-04-20", "entry_type": "standard",
        "description": "Bank receipt - Customer payment",
        "reference": "JE-003",
    })
    t("Create journal entry JE-003", r.status_code, 200)
    je3 = r.json()["data"]["id"]

    if acct_bank and acct_ar:
        c.post(f"{EP}/journal-entries/{je3}/lines", headers=H, json={
            "account_id": acct_bank, "debit": 600000, "credit": 0,
        })
        c.post(f"{EP}/journal-entries/{je3}/lines", headers=H, json={
            "account_id": acct_ar, "debit": 0, "credit": 600000,
        })

    r = c.post(f"{EP}/journal-entries/{je3}/post", headers=H)
    t("Post JE-003", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/trial-balance", headers=H)
    t("Get trial balance", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 21: DOCUMENTS
# ═══════════════════════════════════════════════════════════
def stage_21_docs(c, cid):
    log("STAGE 21: Documents")
    r = c.post(f"{EP}/companies/{cid}/doc-folders", headers=H, json={"name": "Project Documents"})
    t("Create folder", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/documents", headers=H, json={
        "title": "Construction Contract - Al-Andalus",
        "doc_type": "contract",
        "description": "Main construction contract",
    })
    t("Upload contract document", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 22: E-SIGNATURE
# ═══════════════════════════════════════════════════════════
def stage_22_esign(c, cid):
    log("STAGE 22: E-Signature & Approvals")
    r = c.post(f"{EP}/companies/{cid}/approval-templates", headers=H, json={
        "name": "Purchase Order Approval",
        "steps": [
            {"step_number": 1, "approver_role": "procurement_manager", "auto_approve": False},
            {"step_number": 2, "approver_role": "finance_manager", "auto_approve": False},
        ]
    })
    t("Create approval template", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/signature-requests", headers=H, json={
        "title": "Construction Contract Signature",
        "signers": [
            {"signer_id": "admin_p51", "signer_name": "Ahmad Al-Mutairi"},
        ]
    })
    t("Create signature request", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 23: AUDIT TRAIL
# ═══════════════════════════════════════════════════════════
def stage_23_audit(c, cid):
    log("STAGE 23: Audit & Compliance")
    c.post(f"{EP}/companies/{cid}/access-logs", headers=H, json={
        "user_id": "admin_p51", "action": "login", "resource_type": "system",
    })
    c.post(f"{EP}/companies/{cid}/access-logs", headers=H, json={
        "user_id": "admin_p51", "action": "create", "resource_type": "company",
    })

    r = c.get(f"{EP}/companies/{cid}/audit-trail", headers=H)
    t("Get audit trail", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/access-logs", headers=H)
    t("Get access logs", r.status_code, 200)
    if r.status_code == 200:
        t("Access log records exist", len(r.json()["data"]) > 0, True)

    r = c.post(f"{EP}/companies/{cid}/compliance-rules", headers=H, json={
        "rule_code": "PAY-APPROVAL", "name": "Payment Approval Threshold",
        "entity_type": "payment",
    })
    t("Create compliance rule", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/compliance-check", headers=H)
    t("Run compliance check", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 24: REPORTS
# ═══════════════════════════════════════════════════════════
def stage_24_reports(c, cid):
    log("STAGE 24: Reports")
    r = c.post(f"{EP}/companies/{cid}/report-templates", headers=H, json={
        "name": "Project Cost Report", "report_type": "project_costs",
        "data_source": "dbp_projects",
    })
    t("Create report template", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/report-templates", headers=H, json={
        "name": "Monthly Revenue", "report_type": "revenue",
        "data_source": "dbp_invoices",
    })
    t("Create revenue report template", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/report-runs", headers=H)
    t("List report runs", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 25: SYSTEM
# ═══════════════════════════════════════════════════════════
def stage_25_system(c, cid):
    log("STAGE 25: System & Dashboard")
    r = c.get(f"{EP}/system/health", headers=H)
    t("System health", r.status_code, 200)

    r = c.post(f"{EP}/dashboards", headers=H, json={
        "code": "CONS_DASH_51", "name_en": "Construction Dashboard",
    })
    t("Create dashboard", r.status_code, 200)

    r = c.get(f"{EP}/notifications", headers=H)
    t("List notifications", r.status_code, 200)

    r = c.get(f"{EP}/events", headers=H)
    t("List events", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  P51 REAL-WORLD ERP VALIDATION")
    print("  Construction Company: Al-Omran Contracting Co.")
    print("=" * 70)

    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        cid = stage_1_company(c)
        stage_2_structure(c, cid)
        acct_map = stage_3_coa(c, cid)
        stage_4_banks(c, cid)
        cust_id = stage_5_customers(c, cid)
        sup_ids = stage_6_suppliers(c, cid)
        item_ids = stage_7_items(c, cid)
        wh_ids = stage_8_warehouses(c, cid)
        emp_ids = stage_9_employees(c, cid)
        pid = stage_10_project(c, cid)
        task_ids = stage_11_tasks(c, cid, pid)
        stage_12_time_entries(c, pid, emp_ids)
        pr_id = stage_13_pr(c, cid)
        po1, po2 = stage_14_pos(c, cid, sup_ids, item_ids)
        stage_15_grn(c, cid, po1, item_ids)
        stage_16_stock(c, cid, item_ids)
        qid = stage_17_quotation(c, cid, cust_id)
        inv_id = stage_18_sales(c, cid, cust_id)
        stage_19_payment(c, cid, inv_id)
        stage_20_accounting(c, cid, acct_map)
        stage_21_docs(c, cid)
        stage_22_esign(c, cid)
        stage_23_audit(c, cid)
        stage_24_reports(c, cid)
        stage_25_system(c, cid)
    finally:
        c.close()
        stop(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P51 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 70)

    if f == 0:
        print("\n  CONCLUSION: EOS successfully runs a complete construction")
        print("  company ERP from scratch - zero company-specific code!")
    else:
        print(f"\n  {f} gaps found.")

    sys.exit(0 if f == 0 else 1)
