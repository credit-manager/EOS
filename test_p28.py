"""
P28 PROJECT MANAGEMENT TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
p, f = 0, 0
CID = "co_p28"
CID_B = "co_p28b"

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
        for tbl in ("dbp_project_time_entries", "dbp_project_milestones",
                     "dbp_project_tasks", "dbp_projects"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p28', 'tenant_a', 'CO28', 'Test')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p28b', 'tenant_b', 'CO28B', 'Test B')"))
        db.commit()
    finally:
        db.close()

def test_projects(c):
    print("\n--- 1. Projects ---")
    r = c.post(f"{EP}/companies/{CID}/projects", headers=H, json={
        "name": "Website Redesign", "start_date": "2026-01-01",
        "end_date": "2026-06-30", "description": "Full site overhaul",
        "budget": 100000, "manager_id": "emp-manager-1"
    })
    t("Create project", r.status_code, 200)
    pid = r.json()["data"]["id"]
    t("Project has id", bool(pid), True)

    r = c.get(f"{EP}/companies/{CID}/projects", headers=H)
    t("List projects", r.status_code, 200)
    t("Has 1 project", len(r.json()["data"]), 1)
    t("Project name", r.json()["data"][0]["name"], "Website Redesign")
    t("Default status", r.json()["data"][0]["status"], "planning")
    t("Auto code PRJ-", r.json()["data"][0]["code"].startswith("PRJ-"), True)

    r = c.get(f"{EP}/projects/{pid}", headers=H)
    t("Get project", r.status_code, 200)
    t("Task count 0", r.json()["data"]["task_count"], 0)
    t("Completed count 0", r.json()["data"]["completed_task_count"], 0)

    r = c.put(f"{EP}/projects/{pid}", headers=H, json={"budget": 250000, "status": "active"})
    t("Update project", r.status_code, 200)

    r = c.get(f"{EP}/projects/{pid}", headers=H)
    t("Budget updated", r.json()["data"]["budget"], 250000)
    t("Status updated", r.json()["data"]["status"], "active")

    r = c.get(f"{EP}/projects/nonexistent-pid", headers=H)
    t("Get missing project 404", r.status_code, 404)

    r = c.post(f"{EP}/companies/{CID}/projects", headers=H, json={"name": "No Dates"})
    t("Create project missing dates 400", r.status_code, 400)
    return pid

def test_tasks(c, pid):
    print("\n--- 2. Tasks ---")
    r = c.post(f"{EP}/projects/{pid}/tasks", headers=H, json={
        "name": "Design mockups", "assigned_to": "ahmed",
        "priority": "high", "estimated_hours": 16
    })
    t("Create task 1", r.status_code, 200)
    t1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/projects/{pid}/tasks", headers=H, json={
        "name": "Build frontend", "assigned_to": "sara"
    })
    t("Create task 2", r.status_code, 200)
    t2 = r.json()["data"]["id"]

    r = c.post(f"{EP}/projects/{pid}/tasks", headers=H, json={
        "name": "Review palette", "parent_task_id": t1, "assigned_to": "ahmed"
    })
    t("Create subtask", r.status_code, 200)
    tsub = r.json()["data"]["id"]

    r = c.get(f"{EP}/projects/{pid}/tasks", headers=H)
    t("List tasks", r.status_code, 200)
    t("Has 3 tasks", len(r.json()["data"]), 3)
    t("Subtask parent set", r.json()["data"][2]["parent_task_id"], t1)

    r = c.get(f"{EP}/projects/{pid}/tasks?status=todo", headers=H)
    t("Filter todo", len(r.json()["data"]), 3)

    r = c.get(f"{EP}/projects/{pid}/tasks?assigned_to=ahmed", headers=H)
    t("Filter assigned ahmed", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/projects/{pid}", headers=H)
    t("Project task count", r.json()["data"]["task_count"], 3)

    r = c.put(f"{EP}/tasks/{t1}", headers=H, json={"status": "done", "actual_hours": 5})
    t("Update task status", r.status_code, 200)

    r = c.get(f"{EP}/projects/{pid}", headers=H)
    t("Completed count", r.json()["data"]["completed_task_count"], 1)

    r = c.get(f"{EP}/projects/{pid}/tasks?status=done", headers=H)
    t("Filter done", len(r.json()["data"]), 1)

    r = c.post(f"{EP}/projects/{pid}/tasks/reorder", headers=H, json={"task_ids": [t2, t1, tsub]})
    t("Reorder tasks", r.status_code, 200)

    r = c.get(f"{EP}/projects/{pid}/tasks", headers=H)
    t("Order after reorder", [x["id"] for x in r.json()["data"]], [t2, t1, tsub])
    t("Sort order values", [x["sort_order"] for x in r.json()["data"]], [0, 1, 2])

    r = c.put(f"{EP}/tasks/nonexistent-tid", headers=H, json={"status": "done"})
    t("Update missing task 404", r.status_code, 404)

    r = c.post(f"{EP}/projects/{pid}/tasks/reorder", headers=H, json={"task_ids": ["bogus-id"]})
    t("Reorder foreign task 400", r.status_code, 400)
    return (t1, t2, tsub)

def test_milestones(c, pid):
    print("\n--- 3. Milestones ---")
    r = c.post(f"{EP}/projects/{pid}/milestones", headers=H, json={
        "name": "Beta launch", "due_date": "2026-03-31"
    })
    t("Create milestone", r.status_code, 200)
    mid = r.json()["data"]["id"]

    r = c.get(f"{EP}/projects/{pid}/milestones", headers=H)
    t("List milestones", r.status_code, 200)
    t("Has 1 milestone", len(r.json()["data"]), 1)
    t("Milestone pending", r.json()["data"][0]["status"], "pending")

    r = c.post(f"{EP}/milestones/{mid}/complete", headers=H)
    t("Complete milestone", r.status_code, 200)

    r = c.get(f"{EP}/projects/{pid}/milestones", headers=H)
    t("Milestone completed", r.json()["data"][0]["status"], "completed")
    t("Completed at set", bool(r.json()["data"][0]["completed_at"]), True)

    r = c.post(f"{EP}/milestones/{mid}/complete", headers=H)
    t("Re-complete blocked 400", r.status_code, 400)
    return mid

def test_time(c, pid, tasks):
    print("\n--- 4. Time Tracking ---")
    t1, t2, tsub = tasks
    r = c.post(f"{EP}/projects/{pid}/time-entries", headers=H, json={
        "task_id": t1, "employee_id": "emp-1", "work_date": "2026-02-10",
        "hours": 3.5, "notes": "Design work"
    })
    t("Log time 1", r.status_code, 200)

    r = c.post(f"{EP}/projects/{pid}/time-entries", headers=H, json={
        "task_id": t1, "employee_id": "emp-2", "work_date": "2026-02-11", "hours": 2.5
    })
    t("Log time 2", r.status_code, 200)

    r = c.get(f"{EP}/projects/{pid}/time-entries", headers=H)
    t("List entries", r.status_code, 200)
    t("Has 2 entries", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/projects/{pid}/time-entries?employee_id=emp-1", headers=H)
    t("Filter by employee", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/projects/{pid}/time-entries?task_id={t2}", headers=H)
    t("Filter by task", len(r.json()["data"]), 0)

    r = c.get(f"{EP}/projects/{pid}/time-summary", headers=H)
    t("Time summary", r.status_code, 200)
    t("Total hours", r.json()["data"]["total_hours"], 6.0)
    t("By employee count", len(r.json()["data"]["by_employee"]), 2)
    t("Top employee", r.json()["data"]["by_employee"][0]["employee_id"], "emp-1")

    r = c.get(f"{EP}/projects/{pid}/tasks?status=done", headers=H)
    t("Task hours auto-totalled", r.json()["data"][0]["actual_hours"], 11.0)

    r = c.post(f"{EP}/projects/{pid}/time-entries", headers=H, json={
        "task_id": t1, "employee_id": "emp-1", "work_date": "2026-02-12", "hours": -1
    })
    t("Negative hours 400", r.status_code, 400)

    r = c.post(f"{EP}/projects/{pid}/time-entries", headers=H, json={
        "task_id": "bogus-task", "employee_id": "emp-1",
        "work_date": "2026-02-12", "hours": 1
    })
    t("Bad task 404", r.status_code, 404)

def test_tenant_isolation(c, pid_a, mid_a, t1_a):
    print("\n--- 5. Tenant Isolation ---")
    r = c.get(f"{EP}/companies/{CID}/projects", headers=H_B)
    t("Tenant B no projects", len(r.json()["data"]), 0)

    r = c.get(f"{EP}/projects/{pid_a}", headers=H_B)
    t("Tenant B get A project 404", r.status_code, 404)

    r = c.get(f"{EP}/projects/{pid_a}/tasks", headers=H_B)
    t("Tenant B list A tasks 404", r.status_code, 404)

    r = c.put(f"{EP}/tasks/{t1_a}", headers=H_B, json={"status": "todo"})
    t("Tenant B update A task 404", r.status_code, 404)

    r = c.post(f"{EP}/milestones/{mid_a}/complete", headers=H_B)
    t("Tenant B complete A milestone 404", r.status_code, 404)

    r = c.post(f"{EP}/companies/{CID_B}/projects", headers=H_B, json={
        "name": "B Project", "start_date": "2026-01-01", "end_date": "2026-03-01"
    })
    t("Tenant B creates own project", r.status_code, 200)
    pid_b = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID_B}/projects", headers=H_B)
    t("Tenant B sees own project", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/projects/{pid_b}", headers=H)
    t("Tenant A get B project 404", r.status_code, 404)

if __name__ == "__main__":
    print("=" * 60)
    print("P28 PROJECT MANAGEMENT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        pid = test_projects(c)
        tasks = test_tasks(c, pid)
        mid = test_milestones(c, pid)
        test_time(c, pid, tasks)
        test_tenant_isolation(c, pid, mid, tasks[0])
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P28 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
