import pytest

from core.runtime_config import (
    RuntimeConfigurationError,
    cors_origins,
    docs_enabled,
    metrics_enabled,
    parse_bool,
    parse_positive_int,
    request_id_or_generate,
    resolve_auth_mode,
)


def test_auth_mode_defaults_to_test_only_for_explicit_local_environments(monkeypatch):
    monkeypatch.delenv("EOS_AUTH_MODE", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "testing")
    assert resolve_auth_mode() == "test"

    monkeypatch.setenv("ENVIRONMENT", "production")
    assert resolve_auth_mode() == "production"


def test_explicit_auth_mode_is_validated(monkeypatch):
    monkeypatch.setenv("EOS_AUTH_MODE", "production")
    assert resolve_auth_mode() == "production"

    monkeypatch.setenv("EOS_AUTH_MODE", "unsafe")
    with pytest.raises(RuntimeConfigurationError):
        resolve_auth_mode()


def test_cors_rejects_invalid_json_and_wildcard(monkeypatch):
    monkeypatch.setenv("EOS_CORS_ORIGINS", "not-json")
    with pytest.raises(RuntimeConfigurationError):
        cors_origins()

    monkeypatch.setenv("EOS_CORS_ORIGINS", '["*"]')
    with pytest.raises(RuntimeConfigurationError):
        cors_origins()


def test_cors_normalizes_valid_origins(monkeypatch):
    monkeypatch.setenv(
        "EOS_CORS_ORIGINS",
        '["https://app.example.com/", " https://admin.example.com "]',
    )
    assert cors_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_metrics_and_docs_are_opt_in_in_production(monkeypatch):
    monkeypatch.delenv("EOS_METRICS_ENABLED", raising=False)
    monkeypatch.delenv("EOS_ENABLE_DOCS", raising=False)
    assert metrics_enabled("production") is False
    assert docs_enabled("production") is False

    monkeypatch.setenv("EOS_METRICS_ENABLED", "true")
    monkeypatch.setenv("EOS_ENABLE_DOCS", "true")
    assert metrics_enabled("production") is True
    assert docs_enabled("production") is True


def test_strict_env_parsers(monkeypatch):
    monkeypatch.setenv("FEATURE", "false")
    assert parse_bool("FEATURE", True) is False
    monkeypatch.setenv("FEATURE", "invalid")
    with pytest.raises(RuntimeConfigurationError):
        parse_bool("FEATURE", True)

    monkeypatch.setenv("LIMIT", "123")
    assert parse_positive_int("LIMIT", 10) == 123
    monkeypatch.setenv("LIMIT", "0")
    with pytest.raises(RuntimeConfigurationError):
        parse_positive_int("LIMIT", 10)


def test_request_id_is_bounded_and_safe(monkeypatch):
    assert request_id_or_generate("request-123") == "request-123"
    generated = request_id_or_generate("x" * 129)
    assert generated != "x" * 129
    assert len(generated) > 0
    assert request_id_or_generate("bad\nvalue") != "bad\nvalue"
