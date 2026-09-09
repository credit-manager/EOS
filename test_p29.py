"""
P29 FIXED ASSETS MANAGEMENT TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p29"

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
        db.execute(sa("DELETE FROM dbp_asset_depreciation_lines WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_asset_depreciation_runs WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_asset_transfers WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_fixed_assets WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p29', 'tenant_a', 'CO29', 'Test')"))
        db.commit()
    finally:
        db.close()

def test_create_asset(c):
    print("\n--- 1. Create Asset ---")
    r = c.post(f"{EP}/companies/{CID}/fixed-assets", headers=H, json={
        "name": "Laptop Dell XPS", "acquisition_date": "2025-01-01",
        "acquisition_cost": 5000, "useful_life_years": 5,
        "category": "IT Equipment", "location": "Office Riyadh"
    })
    t("Create asset", r.status_code, 200)
    aid = r.json()["data"]["id"]

    r = c.get(f"{EP}/fixed-assets/{aid}", headers=H)
    t("Get asset", r.status_code, 200)
    t("Book value = cost", r.json()["data"]["book_value"], 5000)
    t("Asset active", r.json()["data"]["status"], "active")
    return aid

def test_list_assets(c, aid):
    print("\n--- 2. List Assets ---")
    r = c.get(f"{EP}/companies/{CID}/fixed-assets", headers=H)
    t("List assets", r.status_code, 200)
    t("Has 1 asset", len(r.json()["data"]), 1)

    # Second asset
    c.post(f"{EP}/companies/{CID}/fixed-assets", headers=H, json={
        "name": "Printer HP", "acquisition_date": "2025-03-01",
        "acquisition_cost": 1000, "useful_life_years": 3, "category": "Office"
    })
    r = c.get(f"{EP}/companies/{CID}/fixed-assets", headers=H)
    t("Has 2 assets", len(r.json()["data"]), 2)

def test_depreciation_calc(c, aid):
    print("\n--- 3. Depreciation Calculation ---")
    # Straight line: (5000-0)/5 = 1000/year = 250/quarter
    # Full year 2025
    r = c.post(f"{EP}/companies/{CID}/depreciation/run", headers=H, json={
        "period_start": "2025-01-01", "period_end": "2025-12-31"
    })
    t("Run depreciation", r.status_code, 200)
    run_id = r.json()["data"]["id"]

    r = c.get(f"{EP}/depreciation/runs/{run_id}", headers=H)
    t("Get run", r.status_code, 200)
    t("Has lines", len(r.json()["data"]["lines"]) > 0, True)
    t("Run completed", r.json()["data"]["status"], "completed")

    # Asset should now have book_value = 4000
    r = c.get(f"{EP}/fixed-assets/{aid}", headers=H)
    t("Book value 4000", r.json()["data"]["book_value"], 4000)
    t("Accum dep 1000", r.json()["data"]["accumulated_depreciation"], 1000)

    r = c.get(f"{EP}/companies/{CID}/depreciation/runs", headers=H)
    t("List runs", r.status_code, 200)
    t("Has 1 run", len(r.json()["data"]), 1)

def test_transfer(c, aid):
    print("\n--- 4. Asset Transfer ---")
    r = c.post(f"{EP}/fixed-assets/{aid}/transfer", headers=H, json={
        "to_location": "Office Jeddah", "transfer_date": "2025-06-15"
    })
    t("Transfer asset", r.status_code, 200)

    r = c.get(f"{EP}/fixed-assets/{aid}", headers=H)
    t("New location", r.json()["data"]["location"], "Office Jeddah")

    r = c.get(f"{EP}/fixed-assets/{aid}/transfers", headers=H)
    t("List transfers", r.status_code, 200)
    t("Has 1 transfer", len(r.json()["data"]), 1)

def test_dispose(c):
    print("\n--- 5. Asset Disposal ---")
    r = c.post(f"{EP}/companies/{CID}/fixed-assets", headers=H, json={
        "name": "Old Server", "acquisition_date": "2020-01-01",
        "acquisition_cost": 10000, "useful_life_years": 5
    })
    sid = r.json()["data"]["id"]

    r = c.post(f"{EP}/fixed-assets/{sid}/dispose", headers=H, json={"disposal_date": "2025-06-15"})
    t("Dispose asset", r.status_code, 200)

    r = c.get(f"{EP}/fixed-assets/{sid}", headers=H)
    t("Status disposed", r.json()["data"]["status"], "disposed")

    # Can't dispose again
    r = c.post(f"{EP}/fixed-assets/{sid}/dispose", headers=H, json={"disposal_date": "2025-07-01"})
    t("Re-dispose blocked", r.status_code, 400)

def test_tenant_isolation(c):
    print("\n--- 6. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/fixed-assets", headers=H_B)
    t("Tenant B no assets", len(r.json()["data"]), 0)

if __name__ == "__main__":
    print("=" * 60)
    print("P29 FIXED ASSETS MANAGEMENT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        aid = test_create_asset(c)
        test_list_assets(c, aid)
        test_depreciation_calc(c, aid)
        test_transfer(c, aid)
        test_dispose(c)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P29 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
