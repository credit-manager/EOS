"""Tests for Workflow State Machine — start, transitions, conditions, cancellation."""

import uuid

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_definition(headers: dict, code: str, transitions: list[dict] | None = None) -> dict:
    if transitions is None:
        transitions = [
            {
                "from_state": "draft",
                "to_state": "pending",
                "action": "submit",
                "roles": ["admin", "member"],
                "requires_approval": False,
            },
            {
                "from_state": "pending",
                "to_state": "approved",
                "action": "approve",
                "roles": ["admin"],
                "requires_approval": False,
            },
            {
                "from_state": "pending",
                "to_state": "rejected",
                "action": "reject",
                "roles": ["admin"],
                "requires_approval": False,
            },
        ]
    resp = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": code,
            "name": code.replace("_", " ").title(),
            "states": ["draft", "pending", "approved", "rejected"],
            "initial_state": "draft",
            "transitions": transitions,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _start_workflow(headers: dict, code: str, ref_type: str = "document") -> dict:
    resp = client.post(
        "/api/v1/workflows/instances",
        headers=headers,
        json={
            "workflow_code": code,
            "reference_type": ref_type,
            "reference_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _transition(headers: dict, instance_id: str, action: str) -> dict:
    resp = client.post(
        f"/api/v1/workflows/instances/{instance_id}/transitions",
        headers=headers,
        json={"action": action},
    )
    return resp


# ===================================================================
# 1. Starting a workflow instance
# ===================================================================

class TestStartWorkflow:
    def test_start_instance(self):
        user = _register(f"wf-start-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_start_test")
        instance = _start_workflow(h, "wf_start_test")
        assert instance["status"] == "active"
        assert instance["current_state"] == "draft"
        assert instance["workflow_code"] == "wf_start_test"

    def test_start_multiple_instances(self):
        user = _register(f"wf-start-multi-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_multi_start")
        i1 = _start_workflow(h, "wf_multi_start")
        i2 = _start_workflow(h, "wf_multi_start")
        assert i1["id"] != i2["id"]
        assert i1["current_state"] == "draft"
        assert i2["current_state"] == "draft"

    def test_start_unknown_workflow_fails(self):
        user = _register(f"wf-start-unknown-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        resp = client.post(
            "/api/v1/workflows/instances",
            headers=h,
            json={
                "workflow_code": "nonexistent_workflow",
                "reference_type": "document",
                "reference_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code in (404, 422)


# ===================================================================
# 2. Getting available transitions
# ===================================================================

class TestGetTransitions:
    def test_available_transitions_from_draft(self):
        user = _register(f"wf-trans-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_trans_test")
        instance = _start_workflow(h, "wf_trans_test")

        resp = client.get(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=h,
        )
        assert resp.status_code == 200
        transitions = resp.json()
        codes = [t["code"] for t in transitions]
        assert "submit" in codes
        assert "approve" not in codes

    def test_no_transitions_after_completion(self):
        user = _register(f"wf-trans-done-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_trans_done")
        instance = _start_workflow(h, "wf_trans_done")
        _transition(h, instance["id"], "submit")
        _transition(h, instance["id"], "approve")

        resp = client.get(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=h,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# ===================================================================
# 3. Executing a transition
# ===================================================================

class TestExecuteTransition:
    def test_transition_moves_state(self):
        user = _register(f"wf-exec-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_exec_test")
        instance = _start_workflow(h, "wf_exec_test")

        resp = _transition(h, instance["id"], "submit")
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"
        assert resp.json()["current_state"] == "pending"

    def test_full_lifecycle(self):
        user = _register(f"wf-exec-lc-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_exec_lc")
        instance = _start_workflow(h, "wf_exec_lc")

        r1 = _transition(h, instance["id"], "submit")
        assert r1.json()["current_state"] == "pending"

        r2 = _transition(h, instance["id"], "approve")
        assert r2.json()["current_state"] == "approved"

    def test_transition_to_rejected(self):
        user = _register(f"wf-exec-rej-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_exec_rej")
        instance = _start_workflow(h, "wf_exec_rej")

        _transition(h, instance["id"], "submit")
        resp = _transition(h, instance["id"], "reject")
        assert resp.json()["current_state"] == "rejected"


# ===================================================================
# 4. Invalid transitions are rejected
# ===================================================================

class TestInvalidTransitions:
    def test_skip_state_rejected(self):
        user = _register(f"wf-invalid-skip-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_invalid_skip")
        instance = _start_workflow(h, "wf_invalid_skip")

        resp = _transition(h, instance["id"], "approve")
        assert resp.status_code == 422

    def test_unknown_transition_rejected(self):
        user = _register(f"wf-invalid-unk-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_invalid_unk")
        instance = _start_workflow(h, "wf_invalid_unk")

        resp = _transition(h, instance["id"], "bogus_action")
        assert resp.status_code in (404, 422)

    def test_transition_on_completed_workflow_rejected(self):
        user = _register(f"wf-invalid-comp-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_invalid_comp")
        instance = _start_workflow(h, "wf_invalid_comp")

        _transition(h, instance["id"], "submit")
        _transition(h, instance["id"], "approve")

        resp = _transition(h, instance["id"], "submit")
        assert resp.status_code in (409, 422)


# ===================================================================
# 5. Conditions are evaluated
# ===================================================================

class TestConditionEvaluation:
    def test_condition_gates_transition(self):
        user = _register(f"wf-cond-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cond_test", transitions=[
            {
                "from_state": "draft",
                "to_state": "pending",
                "action": "submit",
                "roles": ["admin", "member"],
                "requires_approval": False,
                "conditions": [{"field": "payload.amount", "op": "gt", "value": 1000}],
            },
            {
                "from_state": "pending",
                "to_state": "approved",
                "action": "approve",
                "roles": ["admin"],
                "requires_approval": False,
            },
        ])
        instance = _start_workflow(h, "wf_cond_test")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=h,
            json={"action": "submit", "payload": {"amount": 500}},
        )
        # Condition gate must reject the transition. The platform contract
        # (test_workflow_v2.test_condition_gates_direct_transition) is a
        # machine-readable 422 whose detail is the reason string; accept
        # the legacy 200/"blocked" shape only for backward compatibility
        # with older deployments.
        assert resp.status_code in (200, 422), resp.text
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("status") == "blocked"
            assert "condition" in str(body.get("detail", "")).lower()
        else:
            detail = resp.json().get("detail", "")
            if isinstance(detail, dict):
                detail = str(detail)
            assert "condition" in detail.lower()

    def test_condition_passes_with_matching_data(self):
        user = _register(f"wf-cond-pass-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cond_pass", transitions=[
            {
                "from_state": "draft",
                "to_state": "pending",
                "action": "submit",
                "roles": ["admin"],
                "requires_approval": False,
                "conditions": [{"field": "payload.priority", "op": "eq", "value": "high"}],
            },
            {
                "from_state": "pending",
                "to_state": "approved",
                "action": "approve",
                "roles": ["admin"],
                "requires_approval": False,
            },
        ])
        instance = _start_workflow(h, "wf_cond_pass")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=h,
            json={"action": "submit", "payload": {"priority": "high"}},
        )
        assert resp.status_code == 200
        assert resp.json().get("current_state") == "pending"

    def test_condition_with_status_filter(self):
        user = _register(f"wf-cond-status-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cond_status", transitions=[
            {
                "from_state": "draft",
                "to_state": "pending",
                "action": "submit",
                "roles": ["admin"],
                "requires_approval": False,
                "conditions": [{"field": "payload.status", "op": "eq", "value": "active"}],
            },
            {
                "from_state": "pending",
                "to_state": "approved",
                "action": "approve",
                "roles": ["admin"],
                "requires_approval": False,
            },
        ])
        instance = _start_workflow(h, "wf_cond_status")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=h,
            json={"action": "submit", "payload": {"status": "inactive"}},
        )
        # Failing a condition gate must never apply the transition. The
        # platform contract (test_workflow_v2) is a machine-readable 422;
        # accept the legacy 200/"blocked" shape only for backward
        # compatibility with older deployments.
        assert resp.status_code in (200, 422), resp.text
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("status") == "blocked"
            assert "condition" in str(body.get("detail", "")).lower()
        else:
            detail = resp.json().get("detail", "")
            if isinstance(detail, dict):
                detail = str(detail)
            assert "condition" in detail.lower()


# ===================================================================
# 6. Cancelling a workflow
# ===================================================================

class TestCancelWorkflow:
    def test_cancel_active_workflow(self):
        user = _register(f"wf-cancel-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cancel_test")
        instance = _start_workflow(h, "wf_cancel_test")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/cancel",
            headers=h,
            json={"reason": "No longer needed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_after_transition(self):
        user = _register(f"wf-cancel-trans-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cancel_trans")
        instance = _start_workflow(h, "wf_cancel_trans")
        _transition(h, instance["id"], "submit")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/cancel",
            headers=h,
            json={"reason": "Changed mind"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_already_completed_rejected(self):
        user = _register(f"wf-cancel-done-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        _create_definition(h, "wf_cancel_done")
        instance = _start_workflow(h, "wf_cancel_done")
        _transition(h, instance["id"], "submit")
        _transition(h, instance["id"], "approve")

        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/cancel",
            headers=h,
            json={"reason": "Too late"},
        )
        assert resp.status_code == 409

    def test_cancel_nonexistent_workflow(self):
        user = _register(f"wf-cancel-no-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/workflows/instances/{fake_id}/cancel",
            headers=h,
            json={"reason": "Ghost"},
        )
        assert resp.status_code == 404

    def test_list_templates(self):
        user = _register(f"wf-templates-{uuid.uuid4()}@example.com")
        h = _headers(user["access_token"])
        resp = client.get("/api/v1/workflows/templates", headers=h)
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) >= 4
        codes = {t["code"] for t in templates}
        assert "purchase_order" in codes
        assert "invoice_approval" in codes
