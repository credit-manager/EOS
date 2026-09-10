import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.security import RowSecurity, _role_matches


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, *_args, **_kwargs):
        return _Result(self.rows)


def test_role_matching_does_not_allow_prefix_privilege_escalation():
    assert _role_matches(["admin"], ["admin"])
    assert _role_matches(["admin:users"], ["admin"])
    assert not _role_matches(["admin123"], ["admin"])
    assert not _role_matches(["administrator"], ["admin"])


def test_row_security_fails_closed_when_in_rule_does_not_match():
    db = _FakeDB([("department_id", "in", "sales,finance", [])])
    assert RowSecurity.get_user_row_filter(db, "entity", ["user"], {"department_id": "hr"}) == "FALSE"


def test_row_security_uses_bind_parameter_for_matching_rule():
    db = _FakeDB([("department_id", "in", "sales,finance", [])])
    where = RowSecurity.get_user_row_filter(db, "entity", ["user"], {"department_id": "sales"})
    params = RowSecurity.get_rls_params(db, "entity", ["user"], {"department_id": "sales"})
    assert where == "department_id = :rls_department_id"
    assert params == {"rls_department_id": "sales"}


def test_row_security_rejects_unsafe_metadata_identifier():
    db = _FakeDB([("department_id;DROP TABLE users", "equals", "x", [])])
    assert RowSecurity.get_user_row_filter(db, "entity", ["user"], {}) == "FALSE"


def test_auth_adapter_rejects_non_access_token(monkeypatch):
    monkeypatch.setenv("EOS_AUTH_MODE", "production")
    from core import production_auth
    from core.auth_adapter import get_current_user

    monkeypatch.setattr(
        production_auth,
        "verify_token",
        lambda _token: {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "type": "refresh",
            "iss": "eos-dbp",
            "aud": "eos-api",
        },
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(SimpleNamespace(credentials="not-an-access-token")))

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token type"
