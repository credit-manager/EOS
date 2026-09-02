"""Security regression tests for the application rate limiter."""
import os

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from core import rate_limit


def _request(client_host="10.0.0.2", headers=None, path="/api/v1/test"):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_untrusted_forwarded_header_is_ignored(monkeypatch):
    monkeypatch.setenv("EOS_TRUSTED_PROXIES", "10.0.0.0/24")
    request = _request("192.168.1.10", {"X-Forwarded-For": "8.8.8.8"})
    assert rate_limit._get_client_ip(request) == "192.168.1.10"


def test_trusted_proxy_uses_valid_original_client(monkeypatch):
    monkeypatch.setenv("EOS_TRUSTED_PROXIES", "10.0.0.0/24")
    request = _request("10.0.0.2", {"X-Forwarded-For": "8.8.8.8, 10.0.0.3"})
    assert rate_limit._get_client_ip(request) == "8.8.8.8"


def test_invalid_proxy_configuration_does_not_trust_forwarded_header(monkeypatch):
    monkeypatch.setenv("EOS_TRUSTED_PROXIES", "not-a-network")
    request = _request("10.0.0.2", {"X-Forwarded-For": "8.8.8.8"})
    assert rate_limit._get_client_ip(request) == "10.0.0.2"


def test_rate_limiter_reads_dict_auth_context(monkeypatch):
    monkeypatch.setenv("EOS_TRUSTED_PROXIES", "")
    request = _request()
    request.state.user = {"id": "user-a", "tenant_id": "tenant-a"}
    limiter = rate_limit.RateLimiter(limits={"ip": 10, "tenant": 20, "user": 5, "endpoint": 10})
    keys = [key for key, _limit in limiter._generate_buckets(request)]
    assert any(key.startswith("rl:tenant:tenant-a:") for key in keys)
    assert any(key.startswith("rl:user:user-a:") for key in keys)


def test_rate_limiter_fails_closed_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EOS_RATE_LIMIT_FAIL_CLOSED", "true")
    monkeypatch.setattr(rate_limit, "_ENGINE", None)
    request = _request()
    limiter = rate_limit.RateLimiter(max_requests=1)
    with pytest.raises(HTTPException) as exc:
        limiter.check(request)
    assert exc.value.status_code == 503
