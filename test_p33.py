"""
P33 E-SIGNATURE & ENHANCED APPROVAL WORKFLOWS TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p33"


def t(name, got, exp):
    global p, f
    if got == exp:
        p += 1
    else:
        f += 1
        print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


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


def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_delegations", "dbp_approval_template_steps",
                     "dbp_approval_templates", "dbp_signature_signers",
                     "dbp_signature_requests"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id = 'co_p33'"))
        db.execute(sa(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en) "
            "VALUES ('co_p33', 'tenant_a', 'COP33', 'P33 Test')"
        ))
        db.commit()
    finally:
        db.close()


# ── Signature Tests ────────────────────────────────────────────

def test_create_signature_request(c):
    print("\n--- 1. Create Signature Request with 2 Signers ---")
    r = c.post(f"{EP}/companies/{CID}/signature-requests", headers=H, json={
        "title": "NDA Agreement",
        "description": "Non-disclosure agreement",
        "signers": [
            {"signer_id": "user1", "signer_email": "user1@test.com",
             "signer_name": "User One", "order_number": 1},
            {"signer_id": "user2", "signer_email": "user2@test.com",
             "signer_name": "User Two", "order_number": 2},
        ]
    })
    t("Create request", r.status_code, 200)
    rid = r.json()["data"]["id"]
    return rid


def test_get_signature_request(c, rid):
    print("\n--- 2. Get Signature Request ---")
    r = c.get(f"{EP}/signature-requests/{rid}", headers=H)
    t("Get request", r.status_code, 200)
    data = r.json()["data"]
    t("Title correct", data["title"], "NDA Agreement")
    t("Status pending", data["status"], "pending")
    t("Has 2 signers", len(data["signers"]), 2)
    t("First signer pending", data["signers"][0]["status"], "pending")
    t("Second signer pending", data["signers"][1]["status"], "pending")


def test_sign_first_signer(c, rid):
    print("\n--- 3. Sign by First Signer (still pending) ---")
    r = c.post(f"{EP}/signature-requests/{rid}/sign", headers=H, json={
        "signer_id": "user1", "signature_data": "base64sig1"
    })
    t("Sign first", r.status_code, 200)
    t("Not all signed", r.json()["data"]["all_signed"], False)

    r = c.get(f"{EP}/signature-requests/{rid}", headers=H)
    data = r.json()["data"]
    t("Request still pending", data["status"], "pending")
    t("First signer signed", data["signers"][0]["status"], "signed")
    t("Second signer still pending", data["signers"][1]["status"], "pending")


def test_sign_second_signer(c, rid):
    print("\n--- 4. Sign by Second Signer (completed) ---")
    r = c.post(f"{EP}/signature-requests/{rid}/sign", headers=H, json={
        "signer_id": "user2", "signature_data": "base64sig2"
    })
    t("Sign second", r.status_code, 200)
    t("All signed", r.json()["data"]["all_signed"], True)

    r = c.get(f"{EP}/signature-requests/{rid}", headers=H)
    data = r.json()["data"]
    t("Request completed", data["status"], "completed")
    t("Completed at set", data["completed_at"] is not None, True)


def test_create_and_reject(c):
    print("\n--- 5. Create and Reject Signature ---")
    r = c.post(f"{EP}/companies/{CID}/signature-requests", headers=H, json={
        "title": "Contract",
        "signers": [
            {"signer_id": "user_r1", "signer_email": "r1@test.com",
             "signer_name": "Rejector"},
        ]
    })
    t("Create reject request", r.status_code, 200)
    rid = r.json()["data"]["id"]

    r = c.post(f"{EP}/signature-requests/{rid}/reject", headers=H, json={
        "signer_id": "user_r1", "reason": "Terms not acceptable"
    })
    t("Reject", r.status_code, 200)

    r = c.get(f"{EP}/signature-requests/{rid}", headers=H)
    data = r.json()["data"]
    t("Request rejected", data["status"], "rejected")
    t("Signer rejected", data["signers"][0]["status"], "rejected")
    t("Rejection reason set", data["signers"][0]["rejection_reason"], "Terms not acceptable")


def test_list_signature_requests(c):
    print("\n--- 6. List Signature Requests ---")
    r = c.get(f"{EP}/companies/{CID}/signature-requests", headers=H)
    t("List requests", r.status_code, 200)
    t("Has requests", len(r.json()["data"]) >= 1, True)


def test_list_signature_requests_filter(c):
    print("\n--- 7. List Signature Requests Filtered ---")
    r = c.get(f"{EP}/companies/{CID}/signature-requests?status=completed", headers=H)
    t("Filter completed", r.status_code, 200)
    for req in r.json()["data"]:
        t("All completed", req["status"], "completed")


def test_get_signature_not_found(c):
    print("\n--- 8. Get Signature Request Not Found ---")
    r = c.get(f"{EP}/signature-requests/nonexistent", headers=H)
    t("404 for missing", r.status_code, 404)


def test_sign_missing_fields(c):
    print("\n--- 9. Sign Missing Fields ---")
    r = c.post(f"{EP}/signature-requests/fake/sign", headers=H, json={
        "signer_id": "user1"
    })
    t("Missing signature_data", r.status_code, 400)


def test_reject_missing_fields(c):
    print("\n--- 10. Reject Missing Fields ---")
    r = c.post(f"{EP}/signature-requests/fake/reject", headers=H, json={
        "signer_id": "user1"
    })
    t("Missing reason", r.status_code, 400)


# ── Approval Template Tests ────────────────────────────────────

def test_create_approval_template(c):
    print("\n--- 11. Create Approval Template ---")
    r = c.post(f"{EP}/companies/{CID}/approval-templates", headers=H, json={
        "name": "Purchase Order Approval",
        "entity_type": "purchase_order",
        "description": "Multi-step PO approval",
        "steps": [
            {"step_number": 1, "approver_role": "manager", "sla_hours": 24,
             "auto_approve": False},
            {"step_number": 2, "approver_role": "director", "sla_hours": 48,
             "auto_approve": False},
        ]
    })
    t("Create template", r.status_code, 200)
    tid = r.json()["data"]["id"]
    return tid


def test_list_approval_templates(c, tid):
    print("\n--- 12. List Approval Templates ---")
    r = c.get(f"{EP}/companies/{CID}/approval-templates", headers=H)
    t("List templates", r.status_code, 200)
    t("Has 1 template", len(r.json()["data"]), 1)
    t("Name correct", r.json()["data"][0]["name"], "Purchase Order Approval")


def test_get_approval_template(c, tid):
    print("\n--- 13. Get Approval Template with Steps ---")
    r = c.get(f"{EP}/approval-templates/{tid}", headers=H)
    t("Get template", r.status_code, 200)
    data = r.json()["data"]
    t("Name correct", data["name"], "Purchase Order Approval")
    t("Entity type", data["entity_type"], "purchase_order")
    t("Has 2 steps", len(data["steps"]), 2)
    t("Step 1 role", data["steps"][0]["approver_role"], "manager")
    t("Step 1 sla", data["steps"][0]["sla_hours"], 24)
    t("Step 2 role", data["steps"][1]["approver_role"], "director")
    t("Step 2 sla", data["steps"][1]["sla_hours"], 48)


def test_approval_template_not_found(c):
    print("\n--- 14. Approval Template Not Found ---")
    r = c.get(f"{EP}/approval-templates/nonexistent", headers=H)
    t("404 for missing", r.status_code, 404)


def test_create_template_missing_fields(c):
    print("\n--- 15. Create Template Missing Fields ---")
    r = c.post(f"{EP}/companies/{CID}/approval-templates", headers=H, json={
        "name": "Incomplete"
    })
    t("Missing steps", r.status_code, 400)


# ── Delegation Tests ───────────────────────────────────────────

def test_create_delegation(c):
    print("\n--- 16. Create Delegation ---")
    r = c.post(f"{EP}/companies/{CID}/delegations", headers=H, json={
        "delegator_id": "manager1",
        "delegate_id": "manager2",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "entity_type": "purchase_order"
    })
    t("Create delegation", r.status_code, 200)
    did = r.json()["data"]["id"]
    return did


def test_list_delegations(c, did):
    print("\n--- 17. List Delegations ---")
    r = c.get(f"{EP}/companies/{CID}/delegations", headers=H)
    t("List delegations", r.status_code, 200)
    t("Has 1 delegation", len(r.json()["data"]), 1)


def test_get_active_delegation(c):
    print("\n--- 18. Get Active Delegation ---")
    r = c.get(f"{EP}/companies/{CID}/delegations/active", headers=H,
              params={"delegator_id": "manager1"})
    t("Get active", r.status_code, 200)
    data = r.json()["data"]
    t("Delegate correct", data["delegate_id"], "manager2")
    t("Entity type", data["entity_type"], "purchase_order")


def test_get_active_delegation_with_entity_type(c):
    print("\n--- 19. Get Active Delegation Filtered by Entity Type ---")
    r = c.get(f"{EP}/companies/{CID}/delegations/active", headers=H,
              params={"delegator_id": "manager1", "entity_type": "purchase_order"})
    t("Get active with entity", r.status_code, 200)


def test_get_active_delegation_wrong_type(c):
    print("\n--- 20. Get Active Delegation Wrong Entity Type ---")
    r = c.get(f"{EP}/companies/{CID}/delegations/active", headers=H,
              params={"delegator_id": "manager1", "entity_type": "invoice"})
    t("404 wrong type", r.status_code, 404)


def test_get_active_delegation_not_found(c):
    print("\n--- 21. Get Active Delegation Not Found ---")
    r = c.get(f"{EP}/companies/{CID}/delegations/active", headers=H,
              params={"delegator_id": "nobody"})
    t("404 not found", r.status_code, 404)


def test_create_delegation_missing_fields(c):
    print("\n--- 22. Create Delegation Missing Fields ---")
    r = c.post(f"{EP}/companies/{CID}/delegations", headers=H, json={
        "delegator_id": "mgr1"
    })
    t("Missing fields", r.status_code, 400)


# ── Tenant Isolation ───────────────────────────────────────────

def test_tenant_isolation_signatures(c):
    print("\n--- 23. Tenant Isolation - Signatures ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    r = c.get(f"{EP}/companies/{CID}/signature-requests", headers=H_B)
    t("Tenant B no requests", r.status_code, 200)
    t("Tenant B empty list", len(r.json()["data"]), 0)


def test_tenant_isolation_templates(c):
    print("\n--- 24. Tenant Isolation - Approval Templates ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    r = c.get(f"{EP}/companies/{CID}/approval-templates", headers=H_B)
    t("Tenant B no templates", r.status_code, 200)
    t("Tenant B empty list", len(r.json()["data"]), 0)


def test_tenant_isolation_delegations(c):
    print("\n--- 25. Tenant Isolation - Delegations ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    r = c.get(f"{EP}/companies/{CID}/delegations", headers=H_B)
    t("Tenant B no delegations", r.status_code, 200)
    t("Tenant B empty list", len(r.json()["data"]), 0)


# ── Additional Tests ───────────────────────────────────────────

def test_create_request_missing_title(c):
    print("\n--- 26. Create Signature Request Missing Title ---")
    r = c.post(f"{EP}/companies/{CID}/signature-requests", headers=H, json={
        "signers": [{"signer_id": "u1"}]
    })
    t("Missing title", r.status_code, 400)


def test_create_request_no_signers(c):
    print("\n--- 27. Create Signature Request No Signers ---")
    r = c.post(f"{EP}/companies/{CID}/signature-requests", headers=H, json={
        "title": "No signers"
    })
    t("No signers", r.status_code, 400)


def test_sign_wrong_signer(c, rid):
    print("\n--- 28. Sign with Wrong Signer ID ---")
    r = c.post(f"{EP}/signature-requests/{rid}/sign", headers=H, json={
        "signer_id": "wrong_user", "signature_data": "sig"
    })
    t("Wrong signer rejected", r.status_code, 400)


def test_create_second_delegation(c):
    print("\n--- 29. Create Second Delegation ---")
    r = c.post(f"{EP}/companies/{CID}/delegations", headers=H, json={
        "delegator_id": "director1",
        "delegate_id": "director2",
        "start_date": "2026-06-01",
        "end_date": "2026-06-30"
    })
    t("Create second delegation", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/delegations", headers=H)
    t("Has 2 delegations", len(r.json()["data"]), 2)


def test_create_third_template(c):
    print("\n--- 30. Create Second Approval Template ---")
    r = c.post(f"{EP}/companies/{CID}/approval-templates", headers=H, json={
        "name": "Leave Request",
        "entity_type": "leave_request",
        "steps": [
            {"step_number": 1, "approver_role": "supervisor", "sla_hours": 12,
             "auto_approve": True}
        ]
    })
    t("Create template 2", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/approval-templates", headers=H)
    t("Has 2 templates", len(r.json()["data"]), 2)


if __name__ == "__main__":
    print("=" * 60)
    print("P33 E-SIGNATURE & APPROVAL WORKFLOWS TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        rid1 = test_create_signature_request(c)
        test_get_signature_request(c, rid1)
        test_sign_first_signer(c, rid1)
        test_sign_second_signer(c, rid1)
        rid2 = test_create_and_reject(c)
        test_list_signature_requests(c)
        test_list_signature_requests_filter(c)
        test_get_signature_not_found(c)
        test_sign_missing_fields(c)
        test_reject_missing_fields(c)
        tid = test_create_approval_template(c)
        test_list_approval_templates(c, tid)
        test_get_approval_template(c, tid)
        test_approval_template_not_found(c)
        test_create_template_missing_fields(c)
        did = test_create_delegation(c)
        test_list_delegations(c, did)
        test_get_active_delegation(c)
        test_get_active_delegation_with_entity_type(c)
        test_get_active_delegation_wrong_type(c)
        test_get_active_delegation_not_found(c)
        test_create_delegation_missing_fields(c)
        test_tenant_isolation_signatures(c)
        test_tenant_isolation_templates(c)
        test_tenant_isolation_delegations(c)
        test_create_request_missing_title(c)
        test_create_request_no_signers(c)
        test_sign_wrong_signer(c, rid1)
        test_create_second_delegation(c)
        test_create_third_template(c)
    finally:
        c.close()
        stop(proc)
    print("\n" + "=" * 60)
    print(f"P33 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
