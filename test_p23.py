"""
P23 FINANCE & TREASURY TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p22"

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
        db.execute(sa("DELETE FROM dbp_budgets WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_payments WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_bank_accounts WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_exchange_rates"))
        db.execute(sa("DELETE FROM dbp_accounts WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_a'"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p22', 'tenant_a', 'CO_P22', 'Test Co')"))
        db.execute(sa("INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, account_type) VALUES ('acc_cash', 'tenant_a', 'co_p22', '1000', 'Cash', 'asset')"))
        db.execute(sa("INSERT INTO dbp_accounts (id, tenant_id, company_id, code, name_en, account_type) VALUES ('acc_rev', 'tenant_a', 'co_p22', '4000', 'Revenue', 'revenue')"))
        db.execute(sa("INSERT INTO dbp_fiscal_years (id, tenant_id, company_id, code, name, start_date, end_date) VALUES ('fy25', 'tenant_a', 'co_p22', 'FY25', 'FY 2025', '2025-01-01', '2025-12-31')"))
        db.commit()
    finally:
        db.close()

def test_bank_accounts(c):
    print("\n--- 1. Bank Accounts ---")
    r = c.post(f"{EP}/companies/{CID}/bank-accounts", headers=H, json={"account_name": "Al Rajhi", "bank_name": "Al Rajhi Bank", "account_number": "123456", "currency_code": "SAR"})
    t("Create bank acc", r.status_code, 200)
    bank_id = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/bank-accounts", headers=H)
    t("List bank accs", r.status_code, 200)
    t("Has bank acc", len(r.json()["data"]), 1)
    return bank_id

def test_payments(c, bank_id):
    print("\n--- 2. Payments ---")
    r = c.post(f"{EP}/companies/{CID}/payments", headers=H, json={
        "payment_type": "receipt", "payment_date": "2025-06-15", "amount": 5000,
        "bank_account_id": bank_id, "payee_name": "Client A"
    })
    t("Create receipt", r.status_code, 200)
    pid = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{CID}/payments", headers=H, json={
        "payment_type": "payment", "payment_date": "2025-06-15", "amount": 1000,
        "bank_account_id": bank_id, "payee_name": "Supplier B"
    })
    t("Create payment", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/payments", headers=H)
    t("List payments", r.status_code, 200)
    t("Has 2 payments", len(r.json()["data"]), 2)

    # Approve receipt -> bank balance increases
    r = c.post(f"{EP}/payments/{pid}/approve", headers=H)
    t("Approve receipt", r.status_code, 200)

    # Verify bank balance
    r = c.get(f"{EP}/companies/{CID}/bank-accounts", headers=H)
    t("Bank balance +5000", r.json()["data"][0]["current_balance"], 5000)

    # Can't re-approve
    r = c.post(f"{EP}/payments/{pid}/approve", headers=H)
    t("Re-approve blocked", r.status_code, 400)

    # Filter by type
    r = c.get(f"{EP}/companies/{CID}/payments?payment_type=payment", headers=H)
    t("Filter by type", len(r.json()["data"]), 1)

def test_exchange_rates(c):
    print("\n--- 3. Exchange Rates ---")
    r = c.post(f"{EP}/exchange-rates", headers=H, json={"from_currency": "USD", "to_currency": "SAR", "rate": 3.75, "rate_date": "2025-06-15", "source": "central_bank"})
    t("Set USD/SAR rate", r.status_code, 200)

    r = c.get(f"{EP}/exchange-rates?from_currency=USD&to_currency=SAR", headers=H)
    t("Get rate", r.status_code, 200)
    t("Rate is 3.75", r.json()["data"]["rate"], 3.75)

    # Convert
    r = c.post(f"{EP}/convert", headers=H, json={"amount": 100, "from_currency": "USD", "to_currency": "SAR"})
    t("Convert 100 USD", r.status_code, 200)
    t("Converted to 375", r.json()["data"]["converted"], 375)

    # Same currency
    r = c.post(f"{EP}/convert", headers=H, json={"amount": 100, "from_currency": "SAR", "to_currency": "SAR"})
    t("Same currency", r.json()["data"]["converted"], 100)

    # Nonexistent rate
    r = c.get(f"{EP}/exchange-rates?from_currency=EUR&to_currency=SAR", headers=H)
    t("Nonexistent rate", r.status_code, 404)

def test_budgets(c):
    print("\n--- 4. Budgets ---")
    r = c.post(f"{EP}/companies/{CID}/budgets", headers=H, json={
        "account_id": "acc_cash", "fiscal_year_id": "fy25", "budget_amount": 100000
    })
    t("Create budget", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/budgets", headers=H)
    t("List budgets", r.status_code, 200)
    t("Has budget", len(r.json()["data"]) >= 1, True)

    r = c.get(f"{EP}/companies/{CID}/budgets/utilization", headers=H)
    t("Utilization", r.status_code, 200)
    t("Has utilization_pct", "utilization_pct" in r.json()["data"][0], True)

if __name__ == "__main__":
    print("=" * 60)
    print("P23 FINANCE & TREASURY TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        bank_id = test_bank_accounts(c)
        test_payments(c, bank_id)
        test_exchange_rates(c)
        test_budgets(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P23 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
