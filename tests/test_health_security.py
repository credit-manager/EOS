import os

from core.health_check import _full_health_allowed


def test_full_health_allowed_outside_production(monkeypatch):
    monkeypatch.setenv("EOS_AUTH_MODE", "testing")
    assert _full_health_allowed(type("Request", (), {"headers": {}})())


def test_full_health_requires_token_in_production(monkeypatch):
    monkeypatch.setenv("EOS_AUTH_MODE", "production")
    monkeypatch.setenv("EOS_HEALTH_TOKEN", "a" * 32)
    request = type("Request", (), {"headers": {"x-health-token": "wrong"}})()
    assert not _full_health_allowed(request)
    request.headers["x-health-token"] = "a" * 32
    assert _full_health_allowed(request)


def test_full_health_rejects_missing_production_token(monkeypatch):
    monkeypatch.setenv("EOS_AUTH_MODE", "production")
    monkeypatch.delenv("EOS_HEALTH_TOKEN", raising=False)
    request = type("Request", (), {"headers": {}})()
    assert not _full_health_allowed(request)
