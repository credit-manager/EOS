
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
    user = _register("pm-proj-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/pm/projects",
        headers=headers,
        json={
            "code": "PM-001",
            "name": "Website Redesign",
            "budget": "25000.00",
            "priority": "high",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "PM-001"
    assert body["name"] == "Website Redesign"
    assert body["status"] == "planning"
    assert body["priority"] == "high"
    assert body["budget"] == "25000.00"


def test_list_projects() -> None:
    user = _register("pm-proj-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/pm/projects", headers=headers, json={"code": "PM-L1", "name": "Alpha"})
    client.post("/api/v1/pm/projects", headers=headers, json={"code": "PM-L2", "name": "Beta"})
    resp = client.get("/api/v1/pm/projects", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_update_project_status_transition() -> None:
    user = _register("pm-proj-transition@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-T1", "name": "Transition"}
    ).json()
    resp = client.patch(
        f"/api/v1/pm/projects/{proj['id']}", headers=headers, json={"status": "active"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_invalid_project_status_transition_rejected() -> None:
    user = _register("pm-proj-invalid-transition@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-T2", "name": "Bad Transition"}
    ).json()
    resp = client.patch(
        f"/api/v1/pm/projects/{proj['id']}", headers=headers, json={"status": "completed"}
    )
    assert resp.status_code == 409


def test_duplicate_project_code_rejected() -> None:
    user = _register("pm-proj-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/pm/projects", headers=headers, json={"code": "PM-DUP", "name": "First"})
    resp = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-DUP", "name": "Second"}
    )
    assert resp.status_code == 409


def test_project_tenant_scoped() -> None:
    user_a = _register("pm-proj-ten-a@example.com")
    user_b = _register("pm-proj-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers_a, json={"code": "PM-SC", "name": "Scoped"}
    ).json()
    resp = client.get(f"/api/v1/pm/projects/{proj['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


def test_delete_project() -> None:
    user = _register("pm-proj-delete@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-D1", "name": "Delete Me"}
    ).json()
    resp = client.delete(f"/api/v1/pm/projects/{proj['id']}", headers=headers)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def test_create_task() -> None:
    user = _register("pm-task-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TC", "name": "Task Project"}
    ).json()
    resp = client.post(
        "/api/v1/pm/tasks",
        headers=headers,
        json={
            "project_id": proj["id"],
            "title": "Design mockups",
            "priority": "high",
            "estimated_hours": "8.00",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Design mockups"
    assert body["status"] == "todo"
    assert body["priority"] == "high"


def test_task_status_transition() -> None:
    user = _register("pm-task-transition@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TT", "name": "Task Trans"}
    ).json()
    task = client.post(
        "/api/v1/pm/tasks",
        headers=headers,
        json={"project_id": proj["id"], "title": "Test Task"},
    ).json()
    resp = client.patch(
        f"/api/v1/pm/tasks/{task['id']}", headers=headers, json={"status": "in_progress"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_invalid_task_status_transition_rejected() -> None:
    user = _register("pm-task-invalid-trans@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TI", "name": "Bad Task Trans"}
    ).json()
    task = client.post(
        "/api/v1/pm/tasks", headers=headers, json={"project_id": proj["id"], "title": "Bad Trans"}
    ).json()
    resp = client.patch(
        f"/api/v1/pm/tasks/{task['id']}", headers=headers, json={"status": "done"}
    )
    assert resp.status_code == 409


def test_delete_task() -> None:
    user = _register("pm-task-delete@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TD", "name": "Del Task"}
    ).json()
    task = client.post(
        "/api/v1/pm/tasks", headers=headers, json={"project_id": proj["id"], "title": "Del Me"}
    ).json()
    resp = client.delete(f"/api/v1/pm/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

def test_create_milestone() -> None:
    user = _register("pm-mile-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-MC", "name": "Milestone Proj"}
    ).json()
    resp = client.post(
        "/api/v1/pm/milestones",
        headers=headers,
        json={"project_id": proj["id"], "name": "Design Complete", "due_date": "2026-12-01"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Design Complete"
    assert body["status"] == "pending"


def test_update_milestone_achieved() -> None:
    user = _register("pm-mile-achieve@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-MA", "name": "Achieve Proj"}
    ).json()
    mile = client.post(
        "/api/v1/pm/milestones",
        headers=headers,
        json={"project_id": proj["id"], "name": "Beta", "due_date": "2026-11-01"},
    ).json()
    resp = client.patch(
        f"/api/v1/pm/milestones/{mile['id']}", headers=headers, json={"status": "achieved"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "achieved"
    assert resp.json()["completed_at"] is not None


# ---------------------------------------------------------------------------
# Time Entries
# ---------------------------------------------------------------------------

def test_create_time_entry() -> None:
    user = _register("pm-time-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TE", "name": "Time Proj"}
    ).json()
    task = client.post(
        "/api/v1/pm/tasks", headers=headers, json={"project_id": proj["id"], "title": "Time Task"}
    ).json()
    resp = client.post(
        "/api/v1/pm/time-entries",
        headers=headers,
        json={"task_id": task["id"], "date": "2026-09-12", "hours": "4.50", "description": "Morning work"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["hours"] == "4.50"
    assert body["description"] == "Morning work"


def test_time_entry_updates_task_actual_hours() -> None:
    user = _register("pm-time-actual@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/pm/projects", headers=headers, json={"code": "PM-TAH", "name": "Hours Proj"}
    ).json()
    task = client.post(
        "/api/v1/pm/tasks", headers=headers, json={"project_id": proj["id"], "title": "Hours Task"}
    ).json()
    client.post(
        "/api/v1/pm/time-entries",
        headers=headers,
        json={"task_id": task["id"], "date": "2026-09-12", "hours": "3.00"},
    )
    client.post(
        "/api/v1/pm/time-entries",
        headers=headers,
        json={"task_id": task["id"], "date": "2026-09-12", "hours": "2.50"},
    )
    updated = client.get(f"/api/v1/pm/tasks/{task['id']}", headers=headers).json()
    assert updated["actual_hours"] == "5.50"
