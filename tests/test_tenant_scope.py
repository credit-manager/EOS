import pytest
from fastapi import HTTPException
from security.tenant_scope import require_tenant_access


def test_same_tenant_allowed():
    assert require_tenant_access({"tenant_id": "A"}, "A") == "a"


def test_cross_tenant_denied():
    with pytest.raises(HTTPException) as exc:
        require_tenant_access({"tenant_id": "A"}, "B")
    assert exc.value.status_code == 403


def test_platform_owner_can_cross_tenant():
    user = {"tenant_id": "A", "is_platform_owner": True}
    assert require_tenant_access(user, "B") == "b"


def test_missing_tenant_denied():
    with pytest.raises(HTTPException) as exc:
        require_tenant_access({}, "A")
    assert exc.value.status_code == 403


def test_superadmin_role_is_not_an_implicit_platform_bypass():
    with pytest.raises(HTTPException) as exc:
        require_tenant_access({"tenant_id": "A", "roles": ["superadmin"]}, "B")
    assert exc.value.status_code == 403


def test_tenant_comparison_is_normalized():
    assert require_tenant_access({"tenant_id": "Tenant-A"}, " tenant-a ") == "tenant-a"
