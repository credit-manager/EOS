"""
P14 AUTO UI / DYNAMIC OPENAPI TESTS
====================================
Tests UI schema generation, form/list/detail schemas,
OpenAPI generation, relationship lookups, and UI security.
"""
import httpx
import subprocess
import sys
import time
import os
sys.path.insert(0, '.')

from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

# Tokens
TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com",
                             roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com",
                             roles=["dynamic_viewer"])
TOKEN_M = create_test_token("tenant_a", user_id="manager", email="manager@test.com",
                             roles=["dynamic_manager"])
TOKEN_O = create_test_token("tenant_a", user_id="operator", email="op@test.com",
                             roles=["dynamic_operator"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}
HEADERS_M = {"Authorization": f"Bearer {TOKEN_M}"}
HEADERS_O = {"Authorization": f"Bearer {TOKEN_O}"}

passed = 0
failed = 0


def test(name, got, expected):
    global passed, failed
    ok = got == expected
    if not ok:
        failed += 1
        print(f"  FAIL - {name}: got {got!r}, expected {expected!r}")
    else:
        passed += 1


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


# ═══════════════════════════════════════════════════════
# SETUP — Create entities
# ═══════════════════════════════════════════════════════

def setup_entities():
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    from models import DBPEntity, DBPField, DBPRelationship

    # Phase 1: Cleanup metadata + physical tables
    db = SessionLocal()
    try:
        for code in ('p14_employee', 'p14_dept', 'p14_salary'):
            db.execute(sa_text(f"DELETE FROM dbp_relationships WHERE entity_id IN "
                               f"(SELECT id FROM dbp_entities WHERE code = '{code}')"))
            db.execute(sa_text(f"DELETE FROM dbp_fields WHERE entity_id IN "
                               f"(SELECT id FROM dbp_entities WHERE code = '{code}')"))
            db.execute(sa_text(f"DELETE FROM dbp_entities WHERE code = '{code}'"))
        for tbl in ('p14_departments', 'p14_employees', 'p14_salary_records'):
            db.execute(sa_text(f"DROP TABLE IF EXISTS {tbl}"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    # Phase 2: Create physical tables
    db = SessionLocal()
    try:
        db.execute(sa_text("""
            CREATE TABLE p14_departments (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                name VARCHAR(255),
                code VARCHAR(20),
                active BOOLEAN DEFAULT true
            )
        """))
        db.execute(sa_text("""
            CREATE TABLE p14_employees (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                name_en VARCHAR(255),
                name_ar VARCHAR(255),
                email VARCHAR(255),
                hire_date DATE,
                salary NUMERIC,
                status VARCHAR(50),
                department_id VARCHAR(36),
                notes TEXT,
                national_id VARCHAR(20),
                phone VARCHAR(30)
            )
        """))
        db.execute(sa_text("""
            CREATE TABLE p14_salary_records (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                amount NUMERIC,
                effective_date DATE,
                employee_id VARCHAR(36)
            )
        """))
        db.commit()
    finally:
        db.close()

    # Phase 3: Create metadata (entities, fields, relationships)
    db = SessionLocal()
    try:
        # Department
        dept = DBPEntity(code="p14_dept", name_en="Department", name_ar="القسم",
                         faculty="hr", table_mapping="p14_departments")
        db.add(dept)
        db.flush()
        db.add_all([
            DBPField(entity_id=dept.id, code="name", label_en="Name",
                     field_type="string", is_required=True,
                     ui_config={"max_length": 100, "order": 1}),
            DBPField(entity_id=dept.id, code="code", label_en="Code",
                     field_type="string", is_required=True,
                     ui_config={"max_length": 10, "order": 2}),
            DBPField(entity_id=dept.id, code="active", label_en="Active",
                     field_type="boolean", ui_config={"order": 3}),
        ])
        db.flush()

        # Employee
        emp = DBPEntity(code="p14_employee", name_en="Employee", name_ar="موظف",
                        faculty="hr", table_mapping="p14_employees")
        db.add(emp)
        db.flush()
        db.add_all([
            DBPField(entity_id=emp.id, code="name_en", label_en="English Name",
                     field_type="string", is_required=True,
                     ui_config={"max_length": 200, "order": 1}),
            DBPField(entity_id=emp.id, code="name_ar", label_en="Arabic Name",
                     field_type="string", ui_config={"order": 2}),
            DBPField(entity_id=emp.id, code="email", label_en="Email",
                     field_type="email", is_required=True,
                     ui_config={"order": 3}),
            DBPField(entity_id=emp.id, code="hire_date", label_en="Hire Date",
                     field_type="date", ui_config={"order": 4}),
            DBPField(entity_id=emp.id, code="salary", label_en="Salary",
                     field_type="currency", is_sensitive=True,
                     writable_roles=["dynamic_manager"],
                     visible_roles=["dynamic_manager"],
                     ui_config={"min": 0, "max": 999999, "order": 5}),
            DBPField(entity_id=emp.id, code="status", label_en="Status",
                     field_type="select",
                     enum_values=["active", "inactive", "on_leave"],
                     ui_config={"order": 6}),
            DBPField(entity_id=emp.id, code="department_id", label_en="Department",
                     field_type="relation", is_required=True,
                     ui_config={"order": 7}),
            DBPField(entity_id=emp.id, code="notes", label_en="Notes",
                     field_type="text",
                     ui_config={"order": 8, "placeholder": "Notes..."}),
            DBPField(entity_id=emp.id, code="national_id", label_en="National ID",
                     field_type="string", is_sensitive=True,
                     writable_roles=["admin"],
                     visible_roles=["admin"],
                     ui_config={"max_length": 10, "order": 9}),
            DBPField(entity_id=emp.id, code="phone", label_en="Phone",
                     field_type="string",
                     writable_roles=["dynamic_operator"],
                     ui_config={"max_length": 20, "order": 10}),
        ])
        db.flush()

        # Salary
        sal = DBPEntity(code="p14_salary", name_en="Salary Record",
                        name_ar="سجل راتب", faculty="finance",
                        table_mapping="p14_salary_records")
        db.add(sal)
        db.flush()
        db.add_all([
            DBPField(entity_id=sal.id, code="amount", label_en="Amount",
                     field_type="currency", is_required=True),
            DBPField(entity_id=sal.id, code="effective_date", label_en="Effective Date",
                     field_type="date", is_required=True),
            DBPField(entity_id=sal.id, code="employee_id", label_en="Employee",
                     field_type="relation", is_required=True),
        ])
        db.flush()

        # Relationships
        db.add_all([
            DBPRelationship(
                entity_id=emp.id, code="employee_department",
                target_entity_code="p14_dept",
                relationship_type="many_to_one",
                source_column="department_id", target_column="id",
                lookup_field="name", is_required=True),
            DBPRelationship(
                entity_id=sal.id, code="salary_employee",
                target_entity_code="p14_employee",
                relationship_type="many_to_one",
                source_column="employee_id", target_column="id",
                lookup_field="name_en", is_required=True),
        ])
        db.commit()
        print("  Setup: 3 entities, 15 fields, 2 relationships")
    except Exception as e:
        db.rollback()
        print(f"  Setup error: {e}")
        raise
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# TEST SECTIONS
# ═══════════════════════════════════════════════════════

def test_form_create(client):
    print("\n--- 1. Form Schema (Create Mode) ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=create", headers=HEADERS_A)
    test("Create form -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Entity code", data["entity_code"], "p14_employee")
    test("Mode", data["mode"], "create")
    test("Has fields", len(data["fields"]) > 0, True)
    test("Has actions", "submit" in data["actions"], True)

    fields = {f["name"]: f for f in data["fields"]}
    test("name_en is text", fields["name_en"]["widget"], "text")
    test("hire_date is date", fields["hire_date"]["widget"], "date")
    test("status is select", fields["status"]["widget"], "select")
    test("notes is textarea", fields["notes"]["widget"], "textarea")
    test("email is email input", fields["email"]["input_type"], "email")
    test("salary has min", fields["salary"]["min"], 0)
    test("salary has max", fields["salary"]["max"], 999999)
    test("name_en has max_length", fields["name_en"]["max_length"], 200)
    test("name_en required", fields["name_en"]["required"], True)
    test("hire_date not required", fields["hire_date"]["required"], False)
    test("salary marked sensitive", fields.get("salary", {}).get("sensitive"), True)
    test("national_id marked sensitive", fields.get("national_id", {}).get("sensitive"), True)
    test("id hidden in create", "id" not in fields, True)
    test("tenant_id hidden", "tenant_id" not in fields, True)


def test_form_edit(client):
    print("\n--- 2. Form Schema (Edit Mode) ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=edit", headers=HEADERS_A)
    test("Edit form -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Mode is edit", data["mode"], "edit")
    test("Has delete action", data["actions"].get("delete"), True)


def test_list_schema(client):
    print("\n--- 3. List Schema ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/list", headers=HEADERS_A)
    test("List schema -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Entity code", data["entity_code"], "p14_employee")
    test("Has columns", len(data["columns"]) > 0, True)
    test("Has filters", len(data["filters"]) > 0, True)
    test("Has pagination", "max_limit" in data["pagination"], True)
    test("Max limit is 500", data["pagination"]["max_limit"], 500)

    cols = {c["field"]: c for c in data["columns"]}
    test("name_en column is string", cols["name_en"]["type"], "string")
    test("salary column maskable", cols["salary"]["maskable"], True)
    test("department_id is relation", cols["department_id"]["type"], "relation")

    date_filters = [f for f in data["filters"] if f["field"] == "hire_date"]
    test("Date filter exists", len(date_filters) > 0, True)
    if date_filters:
        test("Date has gt operator", "gt" in date_filters[0]["operators"], True)


def test_detail_schema(client):
    print("\n--- 4. Detail Schema ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/detail", headers=HEADERS_A)
    test("Detail schema -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Entity code", data["entity_code"], "p14_employee")
    test("Has sections", len(data["sections"]) > 0, True)
    test("Has edit action", data["actions"]["edit"], True)
    test("Has delete action", data["actions"]["delete"], True)

    rel_sections = [s for s in data["sections"] if s.get("type") == "relation"]
    test("Has relationship sections", len(rel_sections) > 0, True)


def test_openapi_schema(client):
    print("\n--- 5. OpenAPI Schema ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/openapi", headers=HEADERS_A)
    test("OpenAPI -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Entity code", data["entity_code"], "p14_employee")
    test("Has schemas", len(data["schemas"]) > 0, True)

    schemas = data["schemas"]
    test("Has Create schema", "CreateP14_Employee" in schemas, True)
    test("Has Record schema", "P14_EmployeeRecord" in schemas, True)
    test("Has List schema", "P14_EmployeeList" in schemas, True)
    test("Has query params", len(data["query_parameters"]) > 0, True)

    param_names = [p["name"] for p in data["query_parameters"]]
    test("Has sort param", "sort" in param_names, True)
    test("Has limit param", "limit" in param_names, True)
    test("Has endpoints", len(data["endpoints"]) > 0, True)
    test("Has list endpoint", "list" in data["endpoints"], True)
    test("Has create endpoint", "create" in data["endpoints"], True)

    create = schemas["CreateP14_Employee"]
    test("Create is object", create["type"], "object")
    test("Create has properties", "properties" in create, True)
    test("Create has required", "required" in create, True)
    test("name_en required in create", "name_en" in create["required"], True)

    props = create["properties"]
    test("status has enum", "enum" in props.get("status", {}), True)


def test_entity_index(client):
    print("\n--- 6. Entity Index ---")
    r = client.get(f"{EP}/ui/entities", headers=HEADERS_A)
    test("Index -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has entities", data["count"] > 0, True)

    codes = [e["code"] for e in data["entities"]]
    test("Contains p14_employee", "p14_employee" in codes, True)
    test("Contains p14_dept", "p14_dept" in codes, True)


def test_relationship_lookup(client):
    print("\n--- 7. Relationship Lookup ---")
    from database import SessionLocal
    from sqlalchemy import text as sa_text

    db = SessionLocal()
    try:
        db.execute(sa_text(
            "INSERT INTO p14_departments (id, tenant_id, name, code, active) "
            "VALUES ('dept-lk-1', :t, 'Engineering', 'ENG', true)"
        ), {"t": "tenant_a"})
        db.commit()
    finally:
        db.close()

    r = client.get(f"{EP}/entities/p14_employee/ui/lookup/department_id?q=Eng",
                   headers=HEADERS_A)
    test("Lookup -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has results", data["count"] > 0, True)
    test("Result has id", "id" in data["results"][0], True)
    test("Result has label", "label" in data["results"][0], True)

    r2 = client.get(f"{EP}/entities/p14_employee/ui/lookup/department_id?q=",
                    headers=HEADERS_A)
    test("Empty search -> 200", r2.status_code, 200)

    r3 = client.get(f"{EP}/entities/p14_employee/ui/lookup/nonexistent_field?q=",
                    headers=HEADERS_A)
    test("Bad field -> 404", r3.status_code, 404)

    db = SessionLocal()
    try:
        db.execute(sa_text("DELETE FROM p14_departments WHERE id = 'dept-lk-1'"))
        db.commit()
    finally:
        db.close()


def test_rbac_visibility(client):
    print("\n--- 8. RBAC Visibility ---")

    # Admin sees all
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=create", headers=HEADERS_A)
    admin_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    test("Admin sees salary", "salary" in admin_f, True)
    test("Admin sees national_id", "national_id" in admin_f, True)

    # Viewer — salary/national_id hidden
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=create", headers=HEADERS_V)
    test("Viewer form -> 200", r.status_code, 200)
    v_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    test("Viewer no salary", "salary" not in v_f, True)
    test("Viewer no national_id", "national_id" not in v_f, True)
    test("Viewer sees name_en", "name_en" in v_f, True)

    # Manager sees salary
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=create", headers=HEADERS_M)
    m_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    test("Manager sees salary", "salary" in m_f, True)
    test("Manager does NOT see national_id (admin only)", "national_id" not in m_f, True)

    # Operator — no salary
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=create", headers=HEADERS_O)
    o_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    test("Operator no salary", "salary" not in o_f, True)
    test("Operator sees phone", "phone" in o_f, True)


def test_rbac_writable(client):
    print("\n--- 9. RBAC Writable ---")

    # Operator — phone writable
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=edit", headers=HEADERS_O)
    o_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    if "phone" in o_f:
        test("Phone writable for operator", o_f["phone"]["readonly"], False)

    # Manager — salary writable
    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=edit", headers=HEADERS_M)
    m_f = {f["name"]: f for f in r.json()["data"]["fields"]}
    test("Salary writable for manager", m_f["salary"]["readonly"], False)


def test_list_rbac(client):
    print("\n--- 10. List Schema RBAC ---")

    r = client.get(f"{EP}/entities/p14_employee/ui/list", headers=HEADERS_A)
    admin_cols = {c["field"]: c for c in r.json()["data"]["columns"]}
    test("Admin list sees salary", "salary" in admin_cols, True)

    r = client.get(f"{EP}/entities/p14_employee/ui/list", headers=HEADERS_V)
    v_cols = {c["field"]: c for c in r.json()["data"]["columns"]}
    test("Viewer list no salary", "salary" not in v_cols, True)
    test("Viewer list sees name_en", "name_en" in v_cols, True)


def test_errors(client):
    print("\n--- 11. Errors ---")
    r = client.get(f"{EP}/entities/nonexistent_entity/ui/form", headers=HEADERS_A)
    test("Bad entity -> 404", r.status_code, 404)

    r = client.get(f"{EP}/entities/nonexistent_entity/ui/list", headers=HEADERS_A)
    test("Bad entity list -> 404", r.status_code, 404)

    r = client.get(f"{EP}/entities/nonexistent_entity/ui/openapi", headers=HEADERS_A)
    test("Bad entity openapi -> 404", r.status_code, 404)

    r = client.get(f"{EP}/entities/p14_employee/ui/form?mode=invalid", headers=HEADERS_A)
    test("Invalid mode -> 400", r.status_code, 400)

    r = client.get(f"{EP}/entities/p14_employee/ui/form")
    test("No auth -> 401", r.status_code, 401)


def test_dept_entity(client):
    print("\n--- 12. Other Entity Types ---")
    r = client.get(f"{EP}/entities/p14_dept/ui/form?mode=create", headers=HEADERS_A)
    test("Dept form -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Dept entity code", data["entity_code"], "p14_dept")
    test("Dept has fields", len(data["fields"]) > 0, True)

    fields = {f["name"]: f for f in data["fields"]}
    test("Dept name is text", fields["name"]["widget"], "text")
    test("Dept code has max_length", fields["code"]["max_length"], 10)


def test_component_schemas(client):
    print("\n--- 13. Component Schemas ---")
    r = client.get(f"{EP}/entities/p14_employee/ui/openapi", headers=HEADERS_A)
    data = r.json()["data"]

    rec = data["schemas"]["P14_EmployeeRecord"]
    test("Record has id property", "id" in rec["properties"], True)

    lst = data["schemas"]["P14_EmployeeList"]
    test("List has data property", "data" in lst["properties"], True)
    test("List has count property", "count" in lst["properties"], True)

    create = data["schemas"]["CreateP14_Employee"]
    req = create.get("required", [])
    test("email required in create", "email" in req, True)
    test("department_id required in create", "department_id" in req, True)


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P14 AUTO UI / DYNAMIC OPENAPI TESTS")
    print("=" * 60)

    print("\nSetup: Creating test entities...")
    setup_entities()

    print("Starting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        test_form_create(client)
        test_form_edit(client)
        test_list_schema(client)
        test_detail_schema(client)
        test_openapi_schema(client)
        test_entity_index(client)
        test_relationship_lookup(client)
        test_rbac_visibility(client)
        test_rbac_writable(client)
        test_list_rbac(client)
        test_errors(client)
        test_dept_entity(client)
        test_component_schemas(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P14 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
