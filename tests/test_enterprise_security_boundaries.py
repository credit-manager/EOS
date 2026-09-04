from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_data_jobs_require_tenant_and_scope_mutations():
    source = (ROOT / "core" / "data_jobs.py").read_text(encoding="utf-8")
    assert "WHERE id=:jid AND tenant_id=:tid" in source
    assert "WHERE tenant_id=:tid" in source
    assert "tenant_id cannot be changed" in source
    assert "Dynamic job requires a tenant-scoped entity table" in source
    assert "filters[\"tenant_id\"]" not in source


def test_data_job_router_requires_authenticated_user():
    source = (ROOT / "routers" / "data_jobs.py").read_text(encoding="utf-8")
    assert "user: dict = Depends(get_current_user)" in source
    assert "user: dict | None" not in source
    assert "execute_job(job_id,tenant_id=_tenant(user))" in source
    assert "cancel_job(job_id,tenant_id=_tenant(user))" in source


def test_payment_router_requires_authentication_and_permissions():
    source = (ROOT / "routers" / "payment_api.py").read_text(encoding="utf-8")
    assert "user: dict | None" not in source
    assert "Depends(get_current_user)" in source
    assert 'require_permission("payments", "create")' in source
    assert 'require_permission("payments", "update")' in source
    assert 'require_permission("payments", "read")' in source


def test_production_role_guard_exists():
    source = (ROOT / "database.py").read_text(encoding="utf-8")
    assert "rolsuper" in source
    assert "rolbypassrls" in source
    assert "database_owner" in source
    assert "Production database role must not be superuser" in source
