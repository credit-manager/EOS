from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"Tenant {email}",
        },
    )
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def test_create_project() -> None:
    user = _register("construction-proj@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/construction/projects",
        headers=headers,
        json={
            "code": "PRJ-001",
            "name": "Downtown Tower",
            "budget": "5000000.00",
            "client_name": "Al-Noor Group",
            "location": "Riyadh, KSA",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "PRJ-001"
    assert body["name"] == "Downtown Tower"
    assert body["status"] == "planning"
    assert body["budget"] == "5000000.00"
    assert body["client_name"] == "Al-Noor Group"


def test_list_projects() -> None:
    user = _register("construction-list-proj@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-L1", "name": "Project One"},
    )
    client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-L2", "name": "Project Two"},
    )
    resp = client.get("/api/construction/projects", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_update_project() -> None:
    user = _register("construction-upd-proj@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-U1", "name": "Old Name"},
    ).json()
    resp = client.patch(
        f"/api/construction/projects/{proj['id']}",
        headers=headers,
        json={"name": "New Name", "status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "active"


def test_delete_project() -> None:
    user = _register("construction-del-proj@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-D1", "name": "Delete Me"},
    ).json()
    resp = client.delete(f"/api/construction/projects/{proj['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_project_code_rejected() -> None:
    user = _register("construction-dup-proj@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-DUP", "name": "First"},
    )
    resp = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-DUP", "name": "Second"},
    )
    assert resp.status_code == 409


def test_project_tenant_scoped() -> None:
    user_a = _register("construction-ten-a@example.com")
    user_b = _register("construction-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers_a,
        json={"code": "PRJ-SC", "name": "Scoped Project"},
    ).json()
    resp = client.get(f"/api/construction/projects/{proj['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


def test_invalid_project_status_rejected() -> None:
    user = _register("construction-invalid-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-INV", "name": "Bad Status", "status": "invalid_status"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

def test_create_contract() -> None:
    user = _register("construction-contract@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-C1", "name": "Contract Test"},
    ).json()
    resp = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-001",
            "title": "Main Contract",
            "counterparty": "BuildCorp",
            "contract_value": "1000000.00",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["contract_number"] == "CON-001"
    assert body["title"] == "Main Contract"
    assert body["counterparty"] == "BuildCorp"
    assert body["contract_value"] == "1000000.00"
    assert body["status"] == "draft"


def test_list_contracts() -> None:
    user = _register("construction-list-con@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-CL", "name": "List Contracts"},
    ).json()
    client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-L1",
            "title": "C1",
            "counterparty": "A",
        },
    )
    resp = client.get(
        f"/api/construction/contracts?project_id={proj['id']}", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_update_contract() -> None:
    user = _register("construction-upd-con@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-UC", "name": "Update Contract"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-U1",
            "title": "Old Title",
            "counterparty": "Old Party",
        },
    ).json()
    resp = client.patch(
        f"/api/construction/contracts/{con['id']}",
        headers=headers,
        json={"title": "New Title", "status": "active"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["status"] == "active"


def test_delete_draft_contract() -> None:
    user = _register("construction-del-con@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-DC", "name": "Delete Contract"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-D1",
            "title": "Delete Me",
            "counterparty": "Party",
        },
    ).json()
    resp = client.delete(f"/api/construction/contracts/{con['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_contract_number_rejected() -> None:
    user = _register("construction-dup-con@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-DC2", "name": "Dup Contract"},
    ).json()
    client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-DUP",
            "title": "First",
            "counterparty": "A",
        },
    )
    resp = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-DUP",
            "title": "Second",
            "counterparty": "B",
        },
    )
    assert resp.status_code == 409


def test_invalid_contract_type_rejected() -> None:
    user = _register("construction-inv-con-type@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-ICT", "name": "Invalid Type"},
    ).json()
    resp = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-ICT",
            "title": "Bad Type",
            "counterparty": "A",
            "contract_type": "invalid",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# BOQ
# ---------------------------------------------------------------------------

def test_create_boq() -> None:
    user = _register("construction-boq@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-BQ", "name": "BOQ Test"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-BQ",
            "title": "BOQ Contract",
            "counterparty": "A",
        },
    ).json()
    resp = client.post(
        "/api/construction/boqs",
        headers=headers,
        json={"contract_id": con["id"], "version": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == 1
    assert resp.json()["status"] == "draft"


def test_add_boq_items() -> None:
    user = _register("construction-boq-items@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-BQI", "name": "BOQ Items"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-BQI",
            "title": "BOQ Items Contract",
            "counterparty": "A",
        },
    ).json()
    boq = client.post(
        "/api/construction/boqs",
        headers=headers,
        json={"contract_id": con["id"], "version": 1},
    ).json()
    item = client.post(
        f"/api/construction/boqs/{boq['id']}/items",
        headers=headers,
        json={
            "item_number": 1,
            "description": "Concrete Works",
            "unit": "m3",
            "quantity": "500",
            "unit_rate": "200.00",
            "amount": "100000.00",
        },
    )
    assert item.status_code == 201
    assert item.json()["description"] == "Concrete Works"
    assert item.json()["amount"] == "100000.00"


def test_boq_status_transition() -> None:
    user = _register("construction-boq-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-BS", "name": "BOQ Status"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-BS",
            "title": "BOQ Status Contract",
            "counterparty": "A",
        },
    ).json()
    boq = client.post(
        "/api/construction/boqs",
        headers=headers,
        json={"contract_id": con["id"], "version": 1},
    ).json()
    resp = client.post(
        f"/api/construction/boqs/{boq['id']}/status?status=submitted",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    resp2 = client.post(
        f"/api/construction/boqs/{boq['id']}/status?status=approved",
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "approved"


def test_invalid_boq_transition_rejected() -> None:
    user = _register("construction-boq-inv-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-BIS", "name": "Invalid BOQ Status"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-BIS",
            "title": "Invalid BOQ",
            "counterparty": "A",
        },
    ).json()
    boq = client.post(
        "/api/construction/boqs",
        headers=headers,
        json={"contract_id": con["id"], "version": 1},
    ).json()
    resp = client.post(
        f"/api/construction/boqs/{boq['id']}/status?status=approved",
        headers=headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Progress Claims
# ---------------------------------------------------------------------------

def test_create_progress_claim() -> None:
    user = _register("construction-claim@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-CLM", "name": "Claim Test"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-CLM",
            "title": "Claim Contract",
            "counterparty": "A",
        },
    ).json()
    resp = client.post(
        "/api/construction/claims",
        headers=headers,
        json={
            "contract_id": con["id"],
            "claim_number": "CLM-001",
            "claim_date": str(date.today()),
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["claim_number"] == "CLM-001"
    assert resp.json()["total_amount"] == "0"


def test_claim_status_transition() -> None:
    user = _register("construction-claim-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-CS", "name": "Claim Status"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-CS",
            "title": "Claim Status Contract",
            "counterparty": "A",
        },
    ).json()
    claim = client.post(
        "/api/construction/claims",
        headers=headers,
        json={
            "contract_id": con["id"],
            "claim_number": "CLM-S1",
            "claim_date": str(date.today()),
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
    ).json()
    for next_status in ["submitted", "approved", "paid"]:
        resp = client.post(
            f"/api/construction/claims/{claim['id']}/status?status={next_status}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status


def test_invalid_claim_transition_rejected() -> None:
    user = _register("construction-claim-inv@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-CIV", "name": "Invalid Claim"},
    ).json()
    con = client.post(
        "/api/construction/contracts",
        headers=headers,
        json={
            "project_id": proj["id"],
            "contract_number": "CON-CIV",
            "title": "Invalid Claim Contract",
            "counterparty": "A",
        },
    ).json()
    claim = client.post(
        "/api/construction/claims",
        headers=headers,
        json={
            "contract_id": con["id"],
            "claim_number": "CLM-INV",
            "claim_date": str(date.today()),
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
    ).json()
    resp = client.post(
        f"/api/construction/claims/{claim['id']}/status?status=paid",
        headers=headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Procurement
# ---------------------------------------------------------------------------

def test_create_procurement() -> None:
    user = _register("construction-proc@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-PR", "name": "Procurement Test"},
    ).json()
    resp = client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-001",
            "title": "Steel Rebar",
            "priority": "high",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["requisition_number"] == "PRQ-001"
    assert resp.json()["priority"] == "high"
    assert resp.json()["status"] == "draft"


def test_procurement_status_transition() -> None:
    user = _register("construction-proc-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-PS", "name": "Procurement Status"},
    ).json()
    proc = client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-S1",
            "title": "Cement",
        },
    ).json()
    for next_status in ["pending_approval", "approved", "ordered", "received"]:
        resp = client.post(
            f"/api/construction/procurements/{proc['id']}/status?status={next_status}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status


def test_invalid_procurement_transition_rejected() -> None:
    user = _register("construction-proc-inv@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-PI", "name": "Invalid Procurement"},
    ).json()
    proc = client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-INV",
            "title": "Invalid",
        },
    ).json()
    resp = client.post(
        f"/api/construction/procurements/{proc['id']}/status?status=ordered",
        headers=headers,
    )
    assert resp.status_code == 409


def test_duplicate_requisition_number_rejected() -> None:
    user = _register("construction-dup-proc@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-DP", "name": "Dup Procurement"},
    ).json()
    client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-DUP",
            "title": "First",
        },
    )
    resp = client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-DUP",
            "title": "Second",
        },
    )
    assert resp.status_code == 409


def test_procurement_tenant_scoped() -> None:
    user_a = _register("construction-proc-ten-a@example.com")
    user_b = _register("construction-proc-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers_a,
        json={"code": "PRJ-PTS", "name": "Tenant Scoped Proc"},
    ).json()
    proc = client.post(
        "/api/construction/procurements",
        headers=headers_a,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-TS",
            "title": "Scoped",
        },
    ).json()
    resp = client.get(
        f"/api/construction/procurements/{proc['id']}", headers=headers_b
    )
    assert resp.status_code in {403, 404}


def test_invalid_priority_rejected() -> None:
    user = _register("construction-inv-priority@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/construction/projects",
        headers=headers,
        json={"code": "PRJ-IP", "name": "Invalid Priority"},
    ).json()
    resp = client.post(
        "/api/construction/procurements",
        headers=headers,
        json={
            "project_id": proj["id"],
            "requisition_number": "PRQ-IP",
            "title": "Bad Priority",
            "priority": "extreme",
        },
    )
    assert resp.status_code == 422
