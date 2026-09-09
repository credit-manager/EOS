"""
P21 ERP FOUNDATION TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN_A}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
HB = {"Authorization": f"Bearer {TOKEN_B}"}

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
        db.execute(sa("DELETE FROM dbp_cost_centers WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_departments WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_fiscal_years WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_branches WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_a'"))
        db.commit()
    finally:
        db.close()

def test_company(c):
    print("\n--- 1. Company ---")
    r = c.post(f"{EP}/companies", headers=H, json={"code": "CO001", "name_en": "Acme Corp", "name_ar": "أكمة", "country": "SA"})
    t("Create company", r.status_code, 200)
    cid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies", headers=H)
    t("List companies", r.status_code, 200)
    t("Has company", len(r.json()["data"]) >= 1, True)

    r = c.get(f"{EP}/companies/{cid}", headers=H)
    t("Get company", r.status_code, 200)
    t("Name correct", r.json()["data"]["name_en"], "Acme Corp")
    t("Country correct", r.json()["data"]["country"], "SA")

    r = c.put(f"{EP}/companies/{cid}", headers=H, json={"city": "Riyadh"})
    t("Update company", r.status_code, 200)
    r = c.get(f"{EP}/companies/{cid}", headers=H)
    t("City updated", r.json()["data"]["city"], "Riyadh")

    r = c.post(f"{EP}/companies", headers=H, json={"code": "CO001", "name_en": "Dup"})
    t("Duplicate code", r.status_code, 409 if r.status_code == 409 else 400)

    r = c.get(f"{EP}/companies/xxx", headers=H)
    t("Get nonexistent", r.status_code, 404)

    return cid

def test_branch(c, cid):
    print("\n--- 2. Branch ---")
    r = c.post(f"{EP}/companies/{cid}/branches", headers=H, json={"code": "BR001", "name_en": "Riyadh HQ", "city": "Riyadh", "is_headquarters": True})
    t("Create branch", r.status_code, 200)
    bid = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{cid}/branches", headers=H, json={"code": "BR002", "name_en": "Jeddah", "city": "Jeddah"})
    t("Create branch 2", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/branches", headers=H)
    t("List branches", r.status_code, 200)
    t("Has 2 branches", len(r.json()["data"]), 2)

    return bid

def test_department(c, cid, bid):
    print("\n--- 3. Department ---")
    r = c.post(f"{EP}/companies/{cid}/departments", headers=H, json={"code": "IT", "name_en": "IT Department", "branch_id": bid})
    t("Create dept", r.status_code, 200)
    it_id = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{cid}/departments", headers=H, json={"code": "DEV", "name_en": "Development", "parent_id": it_id})
    t("Create child dept", r.status_code, 200)

    r = c.post(f"{EP}/companies/{cid}/departments", headers=H, json={"code": "QA", "name_en": "QA", "parent_id": it_id})
    t("Create child dept 2", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/departments", headers=H)
    t("List depts", r.status_code, 200)
    t("Has 3 depts", len(r.json()["data"]), 3)

    r = c.get(f"{EP}/companies/{cid}/departments/tree", headers=H)
    t("Get tree", r.status_code, 200)
    tree = r.json()["data"]
    t("Tree has root", len(tree) >= 1, True)
    t("Root has children", len(tree[0].get("children", [])) >= 1, True)

def test_fiscal_year(c, cid):
    print("\n--- 4. Fiscal Year ---")
    r = c.post(f"{EP}/companies/{cid}/fiscal-years", headers=H, json={"code": "FY2025", "name": "FY 2025", "start_date": "2025-01-01", "end_date": "2025-12-31"})
    t("Create FY", r.status_code, 200)
    fy_id = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{cid}/fiscal-years", headers=H)
    t("List FYs", r.status_code, 200)
    t("Has FY", len(r.json()["data"]) >= 1, True)

    r = c.post(f"{EP}/fiscal-years/{fy_id}/close", headers=H)
    t("Close FY", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/fiscal-years", headers=H)
    t("FY is closed", r.json()["data"][0]["is_closed"], True)

    r = c.post(f"{EP}/fiscal-years/{fy_id}/close", headers=H)
    t("Close already closed", r.status_code, 400)

def test_currency(c):
    print("\n--- 5. Currency ---")
    r = c.get(f"{EP}/currencies", headers=H)
    t("List currencies", r.status_code, 200)
    codes = [x["code"] for x in r.json()["data"]]
    t("Has SAR", "SAR" in codes, True)
    t("Has USD", "USD" in codes, True)
    t("Has 5 currencies", len(r.json()["data"]) >= 5, True)

def test_cost_center(c, cid):
    print("\n--- 6. Cost Center ---")
    r = c.post(f"{EP}/companies/{cid}/cost-centers", headers=H, json={"code": "CC001", "name_en": "Engineering", "budget_amount": 500000})
    t("Create CC", r.status_code, 200)
    cc1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{cid}/cost-centers", headers=H, json={"code": "CC002", "name_en": "Backend Team", "parent_id": cc1, "budget_amount": 200000})
    t("Create child CC", r.status_code, 200)

    r = c.get(f"{EP}/companies/{cid}/cost-centers", headers=H)
    t("List CCs", r.status_code, 200)
    t("Has 2 CCs", len(r.json()["data"]), 2)

def test_tenant_isolation(c, cid):
    print("\n--- 7. Tenant Isolation ---")
    r = c.get(f"{EP}/companies", headers=HB)
    t("Tenant B no companies", len(r.json()["data"]), 0)

    r = c.get(f"{EP}/companies/{cid}", headers=HB)
    t("Tenant B cant see Tenant A company", r.status_code in (403, 404), True)

def test_rbac(c):
    print("\n--- 8. RBAC ---")
    r = c.get(f"{EP}/currencies", headers=HV)
    t("Viewer read currencies", r.status_code, 200)
    r = c.post(f"{EP}/companies", json={"code": "x", "name_en": "x"})
    t("No auth create", r.status_code, 401)

if __name__ == "__main__":
    print("=" * 60)
    print("P21 ERP FOUNDATION TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        cid = test_company(c)
        bid = test_branch(c, cid)
        test_department(c, cid, bid)
        test_fiscal_year(c, cid)
        test_currency(c)
        test_cost_center(c, cid)
        test_tenant_isolation(c, cid)
        test_rbac(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P21 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
