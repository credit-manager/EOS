"""
P27 HUMAN RESOURCES TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p27"

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
        for tbl in ("dbp_payroll_lines", "dbp_payroll_runs", "dbp_attendance",
                     "dbp_leave_requests", "dbp_employees"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p27', 'tenant_a', 'CO27', 'Test')"))
        db.commit()
    finally:
        db.close()

def test_employees(c):
    print("\n--- 1. Employees ---")
    r = c.post(f"{EP}/companies/{CID}/employees", headers=H, json={
        "first_name": "Ahmed", "last_name": "Ali", "hire_date": "2024-01-15",
        "email": "ahmed@test.com", "position": "Developer", "salary": 15000
    })
    t("Create emp", r.status_code, 200)
    eid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/employees", headers=H)
    t("List employees", r.status_code, 200)
    t("Has 1 emp", len(r.json()["data"]), 1)
    t("Emp name", r.json()["data"][0]["first_name"], "Ahmed")

    # Update
    r = c.put(f"{EP}/employees/{eid}", headers=H, json={"salary": 18000, "position": "Sr Developer"})
    t("Update emp", r.status_code, 200)
    return eid

def test_leave(c, eid):
    print("\n--- 2. Leave Requests ---")
    r = c.post(f"{EP}/companies/{CID}/leave-requests", headers=H, json={
        "employee_id": eid, "leave_type": "annual", "start_date": "2025-07-01",
        "end_date": "2025-07-05", "days": 5, "reason": "Vacation"
    })
    t("Create leave", r.status_code, 200)
    lid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/leave-requests", headers=H)
    t("List leaves", r.status_code, 200)
    t("Has 1 leave", len(r.json()["data"]), 1)

    r = c.post(f"{EP}/leave-requests/{lid}/approve", headers=H)
    t("Approve leave", r.status_code, 200)

    # Re-approve should fail
    r = c.post(f"{EP}/leave-requests/{lid}/approve", headers=H)
    t("Re-approve blocked", r.status_code, 400)

def test_attendance(c, eid):
    print("\n--- 3. Attendance ---")
    r = c.post(f"{EP}/companies/{CID}/attendance", headers=H, json={
        "employee_id": eid, "work_date": "2025-06-15",
        "clock_in": "2025-06-15T08:00:00", "clock_out": "2025-06-15T17:00:00",
        "hours_worked": 8, "overtime_hours": 1
    })
    t("Record attendance", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/attendance?employee_id={eid}", headers=H)
    t("List attendance", r.status_code, 200)
    t("Has 1 record", len(r.json()["data"]), 1)

    # Upsert same date
    r = c.post(f"{EP}/companies/{CID}/attendance", headers=H, json={
        "employee_id": eid, "work_date": "2025-06-15", "hours_worked": 9
    })
    t("Upsert attendance", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/attendance?employee_id={eid}", headers=H)
    t("Still 1 record", len(r.json()["data"]), 1)
    t("Hours updated", r.json()["data"][0]["hours_worked"], 9)

def test_payroll(c, eid):
    print("\n--- 4. Payroll ---")
    r = c.post(f"{EP}/companies/{CID}/payroll-runs", headers=H, json={
        "pay_period_start": "2025-06-01", "pay_period_end": "2025-06-30"
    })
    t("Create payroll", r.status_code, 200)
    prid = r.json()["data"]["id"]

    r = c.post(f"{EP}/payroll-runs/{prid}/lines", headers=H, json={
        "employee_id": eid, "basic_salary": 15000, "allowances": 2000,
        "bonus": 500, "deductions": 1000, "tax": 500
    })
    t("Add payroll line", r.status_code, 200)

    r = c.get(f"{EP}/payroll-runs/{prid}", headers=H)
    t("Get payroll", r.status_code, 200)
    t("Has 1 line", len(r.json()["data"]["lines"]), 1)
    t("Net pay", r.json()["data"]["lines"][0]["net_pay"], 16000)
    t("Run gross", r.json()["data"]["total_gross"], 17500)
    t("Run net", r.json()["data"]["total_net"], 16000)

    r = c.get(f"{EP}/companies/{CID}/payroll-runs", headers=H)
    t("List payroll runs", r.status_code, 200)

def test_tenant_isolation(c):
    print("\n--- 5. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/employees", headers=H_B)
    t("Tenant B no employees", len(r.json()["data"]), 0)

if __name__ == "__main__":
    print("=" * 60)
    print("P27 HUMAN RESOURCES TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        eid = test_employees(c)
        test_leave(c, eid)
        test_attendance(c, eid)
        test_payroll(c, eid)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P27 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
