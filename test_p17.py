"""
P17 WORKFLOW & APPROVAL TESTS
================================
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
TOKEN_M = create_test_token("tenant_a", user_id="manager", email="mgr@test.com", roles=["dynamic_manager"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com", roles=["admin"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_M = {"Authorization": f"Bearer {TOKEN_M}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

passed = 0
failed = 0

def test(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL - {name}: got {got!r}, expected {expected!r}")

def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
    )
    time.sleep(5)
    return proc

def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_workflow_crud(client):
    """Section 1: Workflow Definition CRUD"""
    print("\n--- 1. Workflow CRUD ---")

    # Cleanup any leftover from previous run
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    db = SessionLocal()
    try:
        db.execute(sa_text("DELETE FROM dbp_workflow_actions"))
        db.execute(sa_text("DELETE FROM dbp_workflow_instances"))
        db.execute(sa_text("DELETE FROM dbp_workflow_transitions"))
        db.execute(sa_text("DELETE FROM dbp_workflow_states"))
        db.execute(sa_text("DELETE FROM dbp_workflow_definitions"))
        db.commit()
    finally:
        db.close()

    r = client.post(f"{EP}/workflows", headers=HEADERS_A, json={
        "code": "purchase_approval",
        "name_en": "Purchase Approval",
        "name_ar": "اعتماد شراء",
        "entity_code": "p17_orders",
        "description": "Standard purchase approval workflow",
        "sla_hours": 48,
    })
    test("Create workflow -> 200", r.status_code, 200)
    wf_id = r.json()["data"]["id"]

    # List
    r = client.get(f"{EP}/workflows", headers=HEADERS_A)
    test("List workflows -> 200", r.status_code, 200)
    test("Has workflow", len(r.json()["data"]) > 0, True)

    # Get detail
    r = client.get(f"{EP}/workflows/{wf_id}", headers=HEADERS_A)
    test("Get workflow -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has draft state", any(s["code"] == "draft" for s in data["states"]), True)
    test("Has approved state", any(s["code"] == "approved" for s in data["states"]), True)
    test("Draft is initial", any(s["is_initial"] for s in data["states"]), True)
    test("Approved is final", any(s["is_final"] for s in data["states"]), True)
    test("Has 3 states (draft/approved/rejected)", len(data["states"]), 3)

    # Duplicate code
    r = client.post(f"{EP}/workflows", headers=HEADERS_A, json={
        "code": "purchase_approval", "name_en": "Dup",
        "entity_code": "p17_orders",
    })
    test("Duplicate -> 400", r.status_code, 400)

    return wf_id


def test_add_states_transitions(client, wf_id):
    """Section 2: Add states and transitions"""
    print("\n--- 2. States + Transitions ---")

    # Add "manager_review" state
    r = client.post(f"{EP}/workflows/{wf_id}/states", headers=HEADERS_A, json={
        "code": "manager_review",
        "name_en": "Manager Review",
        "state_type": "pending",
        "allowed_roles": ["dynamic_manager"],
    })
    test("Add state -> 200", r.status_code, 200)
    manager_state_id = r.json()["data"]["id"]

    # Add "finance_review" state
    r = client.post(f"{EP}/workflows/{wf_id}/states", headers=HEADERS_A, json={
        "code": "finance_review",
        "name_en": "Finance Review",
        "state_type": "pending",
    })
    test("Add finance state -> 200", r.status_code, 200)
    finance_state_id = r.json()["data"]["id"]

    # Get workflow to find draft and approved IDs
    r = client.get(f"{EP}/workflows/{wf_id}", headers=HEADERS_A)
    states = {s["code"]: s["id"] for s in r.json()["data"]["states"]}
    draft_id = states["draft"]

    # Add transition: draft → manager_review
    r = client.post(f"{EP}/workflows/{wf_id}/transitions", headers=HEADERS_A, json={
        "code": "submit_for_review",
        "name_en": "Submit for Manager Review",
        "from_state_id": draft_id,
        "to_state_id": manager_state_id,
        "action": "approve",
    })
    test("Add transition draft→manager -> 200", r.status_code, 200)

    # Add transition: manager_review → finance_review
    r = client.post(f"{EP}/workflows/{wf_id}/transitions", headers=HEADERS_A, json={
        "code": "manager_approve",
        "name_en": "Manager Approves",
        "from_state_id": manager_state_id,
        "to_state_id": finance_state_id,
        "action": "approve",
        "required_roles": ["dynamic_manager"],
    })
    test("Add transition manager→finance -> 200", r.status_code, 200)

    # Add transition: finance_review → approved
    r = client.post(f"{EP}/workflows/{wf_id}/transitions", headers=HEADERS_A, json={
        "code": "finance_approve",
        "name_en": "Finance Approves",
        "from_state_id": finance_state_id,
        "to_state_id": states["approved"],
        "action": "approve",
    })
    test("Add transition finance→approved -> 200", r.status_code, 200)

    # Add reject transitions
    r = client.post(f"{EP}/workflows/{wf_id}/transitions", headers=HEADERS_A, json={
        "code": "reject_from_draft",
        "name_en": "Reject from Draft",
        "from_state_id": draft_id,
        "to_state_id": states["rejected"],
        "action": "reject",
    })
    test("Add reject from draft -> 200", r.status_code, 200)

    r = client.post(f"{EP}/workflows/{wf_id}/transitions", headers=HEADERS_A, json={
        "code": "reject_from_manager",
        "name_en": "Reject from Manager",
        "from_state_id": manager_state_id,
        "to_state_id": states["rejected"],
        "action": "reject",
    })
    test("Add reject from manager -> 200", r.status_code, 200)

    # Publish
    r = client.post(f"{EP}/workflows/{wf_id}/publish", headers=HEADERS_A)
    test("Publish workflow -> 200", r.status_code, 200)

    # Verify published
    r = client.get(f"{EP}/workflows/{wf_id}", headers=HEADERS_A)
    data = r.json()["data"]
    test("Is published", data["is_published"], True)
    test("Is active", data["is_active"], True)
    test("Has 5 states now", len(data["states"]), 5)
    test("Has transitions", len(data["transitions"]) >= 3, True)

    return manager_state_id, finance_state_id


def test_instance_lifecycle(client, wf_id):
    """Section 3: Instance lifecycle"""
    print("\n--- 3. Instance Lifecycle ---")

    # Start instance
    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": wf_id,
        "entity_code": "p17_orders",
        "record_id": "order-001",
    })
    test("Start instance -> 200", r.status_code, 200)
    inst_id = r.json()["data"]["id"]

    # Get instance
    r = client.get(f"{EP}/workflow-instances/{inst_id}", headers=HEADERS_A)
    test("Get instance -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Status is active", data["status"], "active")
    test("Current state is draft", data["current_state"], "draft")
    test("Has history", len(data["history"]) > 0, True)
    test("History has 'created' action", data["history"][0]["action"], "created")

    # Approve (draft → manager_review)
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve",
                    headers=HEADERS_A, json={"comment": "Submitting for review"})
    test("Approve draft -> 200", r.status_code, 200)
    test("Transition success", r.json()["data"]["success"], True)
    test("Now at manager_review", r.json()["data"]["to_state"], "manager_review")

    # Approve again (manager_review → finance_review) — as manager
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve",
                    headers=HEADERS_M, json={"comment": "Manager approved"})
    test("Manager approve -> 200", r.status_code, 200)
    test("Now at finance_review", r.json()["data"]["to_state"], "finance_review")

    # Approve final (finance_review → approved)
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve",
                    headers=HEADERS_A, json={"comment": "Finance approved"})
    test("Finance approve -> 200", r.status_code, 200)
    test("Now at approved", r.json()["data"]["to_state"], "approved")
    test("Status completed", r.json()["data"]["status"], "completed")

    # Verify full history
    r = client.get(f"{EP}/workflow-instances/{inst_id}", headers=HEADERS_A)
    data = r.json()["data"]
    test("Has completed_at", data["completed_at"] is not None, True)
    actions = [a["action"] for a in data["history"]]
    test("History: created", "created" in actions, True)
    test("History: approve (3x)", actions.count("approve"), 3)


def test_reject_workflow(client, wf_id):
    """Section 4: Reject workflow"""
    print("\n--- 4. Reject Workflow ---")

    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": wf_id,
        "entity_code": "p17_orders",
        "record_id": "order-reject-001",
    })
    inst_id = r.json()["data"]["id"]

    # Approve once
    client.post(f"{EP}/workflow-instances/{inst_id}/approve", headers=HEADERS_A)

    # Reject
    r = client.post(f"{EP}/workflow-instances/{inst_id}/reject",
                    headers=HEADERS_M, json={"comment": "Not approved"})
    test("Reject -> 200", r.status_code, 200)
    test("Status rejected", r.json()["data"]["status"], "rejected")


def test_cancel_workflow(client, wf_id):
    """Section 5: Cancel workflow"""
    print("\n--- 5. Cancel Workflow ---")

    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": wf_id,
        "entity_code": "p17_orders",
        "record_id": "order-cancel-001",
    })
    inst_id = r.json()["data"]["id"]

    # Cancel
    r = client.post(f"{EP}/workflow-instances/{inst_id}/cancel", headers=HEADERS_A)
    test("Cancel -> 200", r.status_code, 200)
    test("Status cancelled", r.json()["data"]["status"], "cancelled")

    # Can't approve cancelled
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve", headers=HEADERS_A)
    test("Approve cancelled -> 400", r.status_code, 400)


def test_invalid_transitions(client, wf_id):
    """Section 6: Invalid transitions"""
    print("\n--- 6. Invalid Transitions ---")

    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": wf_id,
        "entity_code": "p17_orders",
        "record_id": "order-invalid-001",
    })
    inst_id = r.json()["data"]["id"]

    # Approve draft → manager_review first, then try non-existent transition
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve", headers=HEADERS_A)
    test("Approve draft -> manager", r.status_code, 200)

    # Try approve from manager_review (no approve transition to another state from finance side)
    r = client.post(f"{EP}/workflow-instances/{inst_id}/reject", headers=HEADERS_A)
    test("Reject without role -> check", r.status_code, 200)

    # Second approve on same completed instance -> should fail
    r = client.post(f"{EP}/workflow-instances/{inst_id}/approve", headers=HEADERS_A)
    test("Approve already rejected -> 400", r.status_code, 400)


def test_tenant_isolation(client, wf_id):
    """Section 7: Tenant isolation"""
    print("\n--- 7. Tenant Isolation ---")

    # Tenant A instance
    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": wf_id,
        "entity_code": "p17_orders",
        "record_id": "order-tenant-a",
    })
    test("Tenant A instance -> 200", r.status_code, 200)

    # Tenant B can't see tenant A instances
    r = client.get(f"{EP}/workflow-instances", headers=HEADERS_B)
    test("Tenant B list -> 200", r.status_code, 200)
    records = [i["record_id"] for i in r.json()["data"]]
    test("Tenant B doesn't see Tenant A records",
         "order-tenant-a" not in records, True)


def test_list_filters(client, wf_id):
    """Section 8: List filters"""
    print("\n--- 8. List Filters ---")

    r = client.get(f"{EP}/workflow-instances?entity_code=p17_orders", headers=HEADERS_A)
    test("Filter by entity -> 200", r.status_code, 200)
    test("Has results", len(r.json()["data"]) > 0, True)

    r = client.get(f"{EP}/workflow-instances?status=active", headers=HEADERS_A)
    test("Filter by status -> 200", r.status_code, 200)


def test_rbac(client, wf_id):
    """Section 9: RBAC"""
    print("\n--- 9. RBAC ---")

    # Viewer can read
    r = client.get(f"{EP}/workflows", headers=HEADERS_V)
    test("Viewer list workflows -> 200", r.status_code, 200)

    r = client.get(f"{EP}/workflow-instances", headers=HEADERS_V)
    test("Viewer list instances -> 200", r.status_code, 200)

    # No auth — use endpoint that requires get_current_user
    r = client.post(f"{EP}/workflow-instances", json={
        "workflow_id": "x", "entity_code": "x", "record_id": "x",
    })
    test("No auth -> 401", r.status_code, 401)


def test_errors(client):
    """Section 10: Errors"""
    print("\n--- 10. Errors ---")

    r = client.get(f"{EP}/workflows/nonexistent", headers=HEADERS_A)
    test("Bad workflow ID -> 404", r.status_code, 404)

    r = client.get(f"{EP}/workflow-instances/nonexistent", headers=HEADERS_A)
    test("Bad instance ID -> 404", r.status_code, 404)

    # Start with unpublished workflow
    r = client.post(f"{EP}/workflows", headers=HEADERS_A, json={
        "code": "unpublished_wf", "name_en": "Unpublished",
        "entity_code": "p17_orders",
    })
    unp_id = r.json()["data"]["id"]
    r = client.post(f"{EP}/workflow-instances", headers=HEADERS_A, json={
        "workflow_id": unp_id, "entity_code": "p17_orders",
        "record_id": "order-unpub",
    })
    test("Start unpublished -> 400", r.status_code, 400)


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P17 WORKFLOW & APPROVAL TESTS")
    print("=" * 60)

    print("\nStarting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        wf_id = test_workflow_crud(client)
        manager_id, finance_id = test_add_states_transitions(client, wf_id)
        test_instance_lifecycle(client, wf_id)
        test_reject_workflow(client, wf_id)
        test_cancel_workflow(client, wf_id)
        test_invalid_transitions(client, wf_id)
        test_tenant_isolation(client, wf_id)
        test_list_filters(client, wf_id)
        test_rbac(client, wf_id)
        test_errors(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P17 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
