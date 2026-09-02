import pytest
from fastapi import HTTPException

from security.tenant_scope import require_tenant_access


def test_same_tenant_allowed():
    assert require_tenant_access({"tenant_id": "A"}, "A") == "A"


def test_cross_tenant_denied():
    with pytest.raises(HTTPException) as exc:
        require_tenant_access({"tenant_id": "A"}, "B")
    assert exc.value.status_code == 403


def test_platform_owner_can_cross_tenant():
    user = {"tenant_id": "A", "is_platform_owner": True}
    assert require_tenant_access(user, "B") == "B"


def test_missing_tenant_denied():
    with pytest.raises(HTTPException) as exc:
        require_tenant_access({}, "A")
    assert exc.value.status_code == 403
