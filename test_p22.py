"""
P22 ACCOUNTING ENGINE TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0

def t(name, got, exp):
    global p, f
    if got == exp: p += 1
    else: f += 1; print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")

def start():
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc

def stop(proc):
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()

def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa("DELETE FROM dbp_journal_lines"))
        db.execute(sa("DELETE FROM dbp_journal_entries WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_accounts WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_a'"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p22', 'tenant_a', 'CO_P22', 'Test Co')"))
        db.commit()
    finally:
        db.close()

CID = "co_p22"

def test_accounts(c):
    print("\n--- 1. Chart of Accounts ---")
    # Assets
    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "1000", "name_en": "Cash", "account_type": "asset"})
    t("Create cash account", r.status_code, 200)
    cash_id = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "1100", "name_en": "Bank", "account_type": "asset"})
    t("Create bank account", r.status_code, 200)
    bank_id = r.json()["data"]["id"]

    # Liabilities
    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "2000", "name_en": "Accounts Payable", "account_type": "liability"})
    t("Create AP account", r.status_code, 200)
    ap_id = r.json()["data"]["id"]

    # Revenue
    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "4000", "name_en": "Sales Revenue", "account_type": "revenue"})
    t("Create revenue account", r.status_code, 200)
    rev_id = r.json()["data"]["id"]

    # Expense
    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "5000", "name_en": "Cost of Goods", "account_type": "expense"})
    t("Create expense account", r.status_code, 200)
    exp_id = r.json()["data"]["id"]

    # List
    r = c.get(f"{EP}/companies/{CID}/accounts", headers=H)
    t("List accounts", r.status_code, 200)
    t("Has 5 accounts", len(r.json()["data"]), 5)

    # Tree
    r = c.get(f"{EP}/companies/{CID}/accounts/tree", headers=H)
    t("Get tree", r.status_code, 200)

    # Duplicate code
    r = c.post(f"{EP}/companies/{CID}/accounts", headers=H, json={"code": "1000", "name_en": "Dup", "account_type": "asset"})
    t("Duplicate account code", r.status_code, 409)

    return cash_id, bank_id, ap_id, rev_id, exp_id

def test_journal_entries(c, cash_id, bank_id, rev_id, exp_id):
    print("\n--- 2. Journal Entries ---")
    # Create entry
    r = c.post(f"{EP}/companies/{CID}/journal-entries", headers=H, json={
        "entry_date": "2025-06-15", "entry_type": "standard",
        "description": "Sale of goods", "reference": "INV-001"
    })
    t("Create JE", r.status_code, 200)
    je_id = r.json()["data"]["id"]

    # Add lines: debit bank, credit revenue
    r = c.post(f"{EP}/journal-entries/{je_id}/lines", headers=H, json={"account_id": bank_id, "debit": 1000, "credit": 0, "description": "Received payment"})
    t("Add debit line", r.status_code, 200)

    r = c.post(f"{EP}/journal-entries/{je_id}/lines", headers=H, json={"account_id": rev_id, "debit": 0, "credit": 1000, "description": "Revenue recognized"})
    t("Add credit line", r.status_code, 200)

    # Get entry with lines
    r = c.get(f"{EP}/journal-entries/{je_id}", headers=H)
    t("Get JE", r.status_code, 200)
    entry = r.json()["data"]
    t("Has 2 lines", len(entry["lines"]), 2)
    t("Status draft", entry["status"], "draft")

    # Post
    r = c.post(f"{EP}/journal-entries/{je_id}/post", headers=H)
    t("Post JE", r.status_code, 200)
    t("Total debit", r.json()["data"]["total_debit"], 1000)
    t("Total credit", r.json()["data"]["total_credit"], 1000)

    # Verify GL balances updated
    r = c.get(f"{EP}/companies/{CID}/accounts", headers=H)
    accounts = {a["code"]: a for a in r.json()["data"]}
    t("Bank balance +1000", accounts["1100"]["current_balance"], 1000)
    t("Revenue balance -1000", accounts["4000"]["current_balance"], -1000)

    # Cannot re-post
    r = c.post(f"{EP}/journal-entries/{je_id}/post", headers=H)
    t("Re-post blocked", r.status_code, 400)

    # Unbalanced entry
    r = c.post(f"{EP}/companies/{CID}/journal-entries", headers=H, json={"entry_date": "2025-06-15", "entry_type": "standard"})
    je2 = r.json()["data"]["id"]
    c.post(f"{EP}/journal-entries/{je2}/lines", headers=H, json={"account_id": cash_id, "debit": 500, "credit": 0})
    c.post(f"{EP}/journal-entries/{je2}/lines", headers=H, json={"account_id": bank_id, "debit": 0, "credit": 300})
    r = c.post(f"{EP}/journal-entries/{je2}/post", headers=H)
    t("Unbalanced rejected", r.status_code, 400)

def test_trial_balance(c):
    print("\n--- 3. Trial Balance ---")
    r = c.get(f"{EP}/companies/{CID}/trial-balance", headers=H)
    t("Get trial balance", r.status_code, 200)
    tb = r.json()["data"]
    t("Has accounts", len(tb["accounts"]) > 0, True)
    t("Trial balance balanced", tb["is_balanced"], True)
    t("Total debit > 0", tb["total_debit"] > 0, True)

def test_list_entries(c):
    print("\n--- 4. List Entries ---")
    r = c.get(f"{EP}/companies/{CID}/journal-entries", headers=H)
    t("List all", r.status_code, 200)
    t("Has entries", len(r.json()["data"]) >= 1, True)

    r = c.get(f"{EP}/companies/{CID}/journal-entries?status=posted", headers=H)
    t("Filter posted", r.status_code, 200)
    t("Has posted", len(r.json()["data"]) >= 1, True)

if __name__ == "__main__":
    print("=" * 60)
    print("P22 ACCOUNTING ENGINE TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        cash_id, bank_id, ap_id, rev_id, exp_id = test_accounts(c)
        test_journal_entries(c, cash_id, bank_id, rev_id, exp_id)
        test_trial_balance(c)
        test_list_entries(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P22 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
