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
# Departments
# ---------------------------------------------------------------------------

def test_create_department() -> None:
    user = _register("hr-dept-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/hr/departments",
        headers=headers,
        json={"code": "ENG", "name": "Engineering"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "ENG"
    assert body["name"] == "Engineering"
    assert body["status"] == "active"


def test_list_departments() -> None:
    user = _register("hr-dept-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/hr/departments", headers=headers, json={"code": "HR", "name": "Human Resources"})
    client.post("/api/v1/hr/departments", headers=headers, json={"code": "FIN", "name": "Finance"})
    resp = client.get("/api/v1/hr/departments", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_update_department() -> None:
    user = _register("hr-dept-update@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    dept = client.post(
        "/api/v1/hr/departments", headers=headers, json={"code": "MKT", "name": "Marketing"}
    ).json()
    resp = client.patch(
        f"/api/v1/hr/departments/{dept['id']}", headers=headers, json={"name": "Digital Marketing"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Digital Marketing"


def test_delete_department() -> None:
    user = _register("hr-dept-delete@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    dept = client.post(
        "/api/v1/hr/departments", headers=headers, json={"code": "TMP", "name": "Temporary"}
    ).json()
    resp = client.delete(f"/api/v1/hr/departments/{dept['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_department_code_rejected() -> None:
    user = _register("hr-dept-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/hr/departments", headers=headers, json={"code": "OPS", "name": "Operations"})
    resp = client.post(
        "/api/v1/hr/departments", headers=headers, json={"code": "OPS", "name": "Operations 2"}
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

def test_create_employee() -> None:
    user = _register("hr-emp-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-001",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "hire_date": "2026-01-15",
            "job_title": "Software Engineer",
            "salary": "15000.00",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["employee_number"] == "EMP-001"
    assert body["first_name"] == "John"
    assert body["status"] == "active"


def test_list_employees() -> None:
    user = _register("hr-emp-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-L1",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Developer",
        },
    )
    resp = client.get("/api/v1/hr/employees", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_update_employee() -> None:
    user = _register("hr-emp-update@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-U1",
            "first_name": "Bob",
            "last_name": "Jones",
            "email": "bob@example.com",
            "hire_date": "2026-03-01",
            "job_title": "Analyst",
        },
    ).json()
    resp = client.patch(
        f"/api/v1/hr/employees/{emp['id']}",
        headers=headers,
        json={"job_title": "Senior Analyst", "status": "inactive"},
    )
    assert resp.status_code == 200
    assert resp.json()["job_title"] == "Senior Analyst"
    assert resp.json()["status"] == "inactive"


def test_duplicate_employee_number_rejected() -> None:
    user = _register("hr-emp-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-DUP",
            "first_name": "X",
            "last_name": "Y",
            "email": "xy@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Tester",
        },
    )
    resp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-DUP",
            "first_name": "A",
            "last_name": "B",
            "email": "ab@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Tester",
        },
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def test_create_attendance() -> None:
    user = _register("hr-att-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-ATT1",
            "first_name": "Carol",
            "last_name": "White",
            "email": "carol@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Manager",
        },
    ).json()
    resp = client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={"employee_id": emp["id"], "date": "2026-09-12", "status": "present"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "present"


def test_duplicate_attendance_rejected() -> None:
    user = _register("hr-att-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-ATTD",
            "first_name": "Dave",
            "last_name": "Lee",
            "email": "dave@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Clerk",
        },
    ).json()
    client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={"employee_id": emp["id"], "date": "2026-09-10", "status": "present"},
    )
    resp = client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={"employee_id": emp["id"], "date": "2026-09-10", "status": "late"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Leave Requests
# ---------------------------------------------------------------------------

def test_create_leave_request() -> None:
    user = _register("hr-leave-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-LV1",
            "first_name": "Eve",
            "last_name": "Martin",
            "email": "eve@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Designer",
        },
    ).json()
    resp = client.post(
        "/api/v1/hr/leave-requests",
        headers=headers,
        json={
            "employee_id": emp["id"],
            "leave_type": "annual",
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "days": 5,
            "reason": "Vacation",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["leave_type"] == "annual"
    assert body["status"] == "pending"


def test_approve_leave_request() -> None:
    user = _register("hr-leave-approve@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-LV2",
            "first_name": "Frank",
            "last_name": "Brown",
            "email": "frank@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Accountant",
        },
    ).json()
    lr = client.post(
        "/api/v1/hr/leave-requests",
        headers=headers,
        json={
            "employee_id": emp["id"],
            "leave_type": "sick",
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "days": 3,
        },
    ).json()
    resp = client.post(f"/api/v1/hr/leave-requests/{lr['id']}/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_reject_leave_request() -> None:
    user = _register("hr-leave-reject@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-LV3",
            "first_name": "Grace",
            "last_name": "Davis",
            "email": "grace@example.com",
            "hire_date": "2026-01-01",
            "job_title": "HR Specialist",
        },
    ).json()
    lr = client.post(
        "/api/v1/hr/leave-requests",
        headers=headers,
        json={
            "employee_id": emp["id"],
            "leave_type": "personal",
            "start_date": "2026-12-01",
            "end_date": "2026-12-01",
            "days": 1,
        },
    ).json()
    resp = client.post(f"/api/v1/hr/leave-requests/{lr['id']}/reject", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_invalid_leave_status_rejected() -> None:
    user = _register("hr-leave-invalid@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-LVI",
            "first_name": "Hank",
            "last_name": "Wilson",
            "email": "hank@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Technician",
        },
    ).json()
    resp = client.post(
        "/api/v1/hr/leave-requests",
        headers=headers,
        json={
            "employee_id": emp["id"],
            "leave_type": "annual",
            "start_date": "2027-01-01",
            "end_date": "2027-01-05",
            "days": 5,
            "reason": "Trip",
        },
    )
    assert resp.status_code == 201
    # Trying to approve an already approved leave should fail
    lr = resp.json()
    client.post(f"/api/v1/hr/leave-requests/{lr['id']}/approve", headers=headers)
    resp2 = client.post(f"/api/v1/hr/leave-requests/{lr['id']}/approve", headers=headers)
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

def test_create_payroll_run() -> None:
    user = _register("hr-pay-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/hr/payroll-runs",
        headers=headers,
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["period_start"] == "2026-09-01"


def test_create_payroll_line() -> None:
    user = _register("hr-pay-line@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    pr = client.post(
        "/api/v1/hr/payroll-runs",
        headers=headers,
        json={"period_start": "2026-08-01", "period_end": "2026-08-31"},
    ).json()
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers,
        json={
            "employee_number": "EMP-PAY1",
            "first_name": "Ivan",
            "last_name": "Garcia",
            "email": "ivan@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Developer",
            "salary": "20000.00",
        },
    ).json()
    resp = client.post(
        "/api/v1/hr/payroll-lines",
        headers=headers,
        json={
            "payroll_run_id": pr["id"],
            "employee_id": emp["id"],
            "base_salary": "20000.00",
            "deductions": "3000.00",
            "net_pay": "17000.00",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["net_pay"] == "17000.00"


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

def test_employee_tenant_scoped() -> None:
    user_a = _register("hr-ten-a@example.com")
    user_b = _register("hr-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    emp = client.post(
        "/api/v1/hr/employees",
        headers=headers_a,
        json={
            "employee_number": "EMP-SC",
            "first_name": "Scoped",
            "last_name": "Emp",
            "email": "scoped@example.com",
            "hire_date": "2026-01-01",
            "job_title": "Tester",
        },
    ).json()
    resp = client.get(f"/api/v1/hr/employees/{emp['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

def test_hr_requires_auth() -> None:
    resp = client.get("/api/v1/hr/departments")
    assert resp.status_code == 401


def test_invalid_department_status_rejected() -> None:
    user = _register("hr-dept-invalid@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/hr/departments",
        headers=headers,
        json={"code": "BAD", "name": "Bad Status", "status": "unknown"},
    )
    assert resp.status_code == 422
