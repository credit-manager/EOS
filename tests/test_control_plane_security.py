import pytest
from fastapi import HTTPException
from starlette.requests import Request

from core.control_plane_security import validate_tenant_provisioning_request


def _request(path: str, method: str, payload: bytes):
    headers = [(b"content-type", b"application/json")]

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_tenant_provisioning_rejects_missing_or_weak_password():
    request = _request(
        "/api/v1/control/tenants",
        "POST",
        b'{"name":"Acme","industry_code":"construction","admin_email":"owner@example.com"}',
    )
    with pytest.raises(HTTPException, match="admin_password"):
        await validate_tenant_provisioning_request(request)

    request = _request(
        "/api/v1/control/tenants",
        "POST",
        b'{"admin_password":"short"}',
    )
    with pytest.raises(HTTPException, match="admin_password"):
        await validate_tenant_provisioning_request(request)


@pytest.mark.asyncio
async def test_tenant_provisioning_accepts_strong_password_and_ignores_other_routes():
    request = _request(
        "/api/v1/control/tenants",
        "POST",
        b'{"admin_password":"correct-horse-battery-staple"}',
    )
    assert await validate_tenant_provisioning_request(request) is None

    request = _request(
        "/api/v1/control/tenants/tenant_a",
        "PUT",
        b'{"admin_password":"short"}',
    )
    assert await validate_tenant_provisioning_request(request) is None
