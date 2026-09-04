from core.production_config import validate_production_config


def _base_env(monkeypatch):
    values = {
        "EOS_AUTH_MODE": "production",
        "EOS_ENVIRONMENT": "production",
        "EOS_SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql://user:password@localhost:5432/eos",
        "EOS_2FA_ENCRYPTION_KEY": "x" * 44,
        "EOS_EMAIL_PROVIDER": "smtp",
        "EOS_SMTP_HOST": "smtp.example.com",
        "EOS_SMTP_USERNAME": "user",
        "EOS_SMTP_PASSWORD": "password",
        "EOS_FROM_EMAIL": "noreply@example.com",
        "EOS_PAYMENT_MODE": "disabled",
        "EOS_FRONTEND_URL": "https://app.example.com",
        "EOS_CORS_ORIGINS": '["https://app.example.com"]',
        "EOS_ALLOWED_HOSTS": "app.example.com",
        "EOS_TRUSTED_HOSTS_ENABLED": "true",
        "EOS_DISABLE_DOCS": "true",
        "EOS_RATE_LIMIT_FAIL_CLOSED": "true",
        "EOS_TRUSTED_PROXIES": "10.0.0.0/8",
        "POSTGRES_USER": "eos",
        "POSTGRES_PASSWORD": "password",
        "POSTGRES_DB": "eos",
        "DOMAIN": "https://app.example.com",
        "EOS_METRICS_TOKEN": "m" * 64,
        "EOS_HEALTH_TOKEN": "h" * 64,
        "EOS_RUNTIME_SCHEMA": "false",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("core.production_config._check_database_role", lambda: ("DATABASE_ROLE_RLS_SAFE", "OK", True))


def test_production_allows_disabled_payments(monkeypatch):
    _base_env(monkeypatch)
    failures = [name for name, status, critical in validate_production_config() if critical and status != "OK"]
    assert failures == []


def test_production_requires_2fa_key(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("EOS_2FA_ENCRYPTION_KEY")
    failures = {name for name, status, critical in validate_production_config() if critical and status != "OK"}
    assert "EOS_2FA_ENCRYPTION_KEY" in failures


def test_production_requires_live_stripe_key_when_enabled(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("EOS_PAYMENT_MODE", "stripe")
    monkeypatch.setenv("EOS_STRIPE_SECRET_KEY", "sk_live_" + "x" * 20)
    failures = [name for name, status, critical in validate_production_config() if critical and status != "OK"]
    assert failures == []
