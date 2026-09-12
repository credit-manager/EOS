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
# Contacts
# ---------------------------------------------------------------------------

def test_create_contact() -> None:
    user = _register("crm-contact@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "company": "Acme Corp",
            "job_title": "Manager",
            "lead_source": "website",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "John"
    assert body["last_name"] == "Doe"
    assert body["email"] == "john@example.com"
    assert body["status"] == "lead"


def test_list_contacts() -> None:
    user = _register("crm-list-contacts@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "A", "last_name": "B", "email": "a@b.com"},
    )
    client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "C", "last_name": "D", "email": "c@d.com"},
    )
    resp = client.get("/api/v1/crm/contacts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_update_contact() -> None:
    user = _register("crm-update-contact@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Old", "last_name": "Name", "email": "old@name.com"},
    ).json()
    resp = client.patch(
        f"/api/v1/crm/contacts/{contact['id']}",
        headers=headers,
        json={"first_name": "New", "status": "customer"},
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "New"
    assert resp.json()["status"] == "customer"


def test_delete_contact() -> None:
    user = _register("crm-delete-contact@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Del", "last_name": "Me", "email": "del@me.com"},
    ).json()
    resp = client.delete(f"/api/v1/crm/contacts/{contact['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_contact_email_rejected() -> None:
    user = _register("crm-dup-contact@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "A", "last_name": "B", "email": "dup@test.com"},
    )
    resp = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "C", "last_name": "D", "email": "dup@test.com"},
    )
    assert resp.status_code == 409


def test_contact_tenant_scoped() -> None:
    user_a = _register("crm-ten-a@example.com")
    user_b = _register("crm-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers_a,
        json={"first_name": "X", "last_name": "Y", "email": "x@y.com"},
    ).json()
    resp = client.get(f"/api/v1/crm/contacts/{contact['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


def test_invalid_contact_status_rejected() -> None:
    user = _register("crm-invalid-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Bad", "last_name": "Status", "email": "bad@status.com", "status": "invalid"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

def test_create_opportunity() -> None:
    user = _register("crm-opp@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/crm/opportunities",
        headers=headers,
        json={
            "title": "Big Deal",
            "value": "100000.00",
            "currency": "USD",
            "stage": "prospecting",
            "probability": 20,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Big Deal"
    assert body["value"] == "100000.00"
    assert body["stage"] == "prospecting"


def test_opportunity_stage_transition() -> None:
    user = _register("crm-stage@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    opp = client.post(
        "/api/v1/crm/opportunities",
        headers=headers,
        json={"title": "Stage Test", "stage": "prospecting"},
    ).json()
    resp = client.post(
        f"/api/v1/crm/opportunities/{opp['id']}/stage",
        headers=headers,
        params={"stage": "qualification"},
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "qualification"


def test_opportunity_invalid_stage_transition_rejected() -> None:
    user = _register("crm-inv-stage@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    opp = client.post(
        "/api/v1/crm/opportunities",
        headers=headers,
        json={"title": "Bad Stage", "stage": "prospecting"},
    ).json()
    resp = client.post(
        f"/api/v1/crm/opportunities/{opp['id']}/stage",
        headers=headers,
        params={"stage": "closed_won"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

def test_create_activity() -> None:
    user = _register("crm-activity@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Act", "last_name": "User", "email": "act@user.com"},
    ).json()
    resp = client.post(
        "/api/v1/crm/activities",
        headers=headers,
        json={
            "contact_id": contact["id"],
            "activity_type": "call",
            "subject": "Follow up call",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["activity_type"] == "call"
    assert body["subject"] == "Follow up call"
    assert body["status"] == "pending"


def test_complete_activity() -> None:
    user = _register("crm-complete-activity@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Cmp", "last_name": "User", "email": "cmp@user.com"},
    ).json()
    activity = client.post(
        "/api/v1/crm/activities",
        headers=headers,
        json={
            "contact_id": contact["id"],
            "activity_type": "email",
            "subject": "Send proposal",
        },
    ).json()
    resp = client.post(f"/api/v1/crm/activities/{activity['id']}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def test_create_note() -> None:
    user = _register("crm-note@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Note", "last_name": "User", "email": "note@user.com"},
    ).json()
    resp = client.post(
        "/api/v1/crm/notes",
        headers=headers,
        json={
            "contact_id": contact["id"],
            "content": "Important follow-up note",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "Important follow-up note"


def test_list_notes() -> None:
    user = _register("crm-list-notes@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "List", "last_name": "User", "email": "list@user.com"},
    ).json()
    client.post(
        "/api/v1/crm/notes",
        headers=headers,
        json={"contact_id": contact["id"], "content": "Note 1"},
    )
    client.post(
        "/api/v1/crm/notes",
        headers=headers,
        json={"contact_id": contact["id"], "content": "Note 2"},
    )
    resp = client.get("/api/v1/crm/notes", headers=headers, params={"contact_id": contact["id"]})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_delete_note() -> None:
    user = _register("crm-delete-note@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    contact = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={"first_name": "Del", "last_name": "Note", "email": "del@note.com"},
    ).json()
    note = client.post(
        "/api/v1/crm/notes",
        headers=headers,
        json={"contact_id": contact["id"], "content": "Delete me"},
    ).json()
    resp = client.delete(f"/api/v1/crm/notes/{note['id']}", headers=headers)
    assert resp.status_code == 204
