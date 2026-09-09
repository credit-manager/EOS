import pytest

from core.production_config import validate_production_config


def _set_valid_production(monkeypatch):
    values = {
        "EOS_AUTH_MODE": "production",
        "EOS_SECRET_KEY": "A" * 64,
        "EOS_ALGORITHM": "HS256",
        "EOS_JWT_ISSUER": "eos-dbp",
        "EOS_JWT_AUDIENCE": "eos-api",
        "DATABASE_URL": "postgresql://eos:password@db.example.com:5432/eos",
        "EOS_EMAIL_PROVIDER": "smtp",
        "EOS_SMTP_HOST": "smtp.example.com",
        "EOS_SMTP_USERNAME": "mailer",
        "EOS_SMTP_PASSWORD": "mail-password",
        "EOS_FROM_EMAIL": "noreply@example.com",
        "EOS_PAYMENT_MODE": "stripe",
        "EOS_STRIPE_SECRET_KEY": "sk_live_ci_9f7a6c3b2e1d4a8c",
        "EOS_FRONTEND_URL": "https://app.example.com",
        "EOS_CORS_ORIGINS": '["https://app.example.com"]',
        "EOS_ALLOWED_HOSTS": "app.example.com,api.example.com",
        "POSTGRES_USER": "eos",
        "POSTGRES_PASSWORD": "database-password",
        "POSTGRES_DB": "eos",
        "DOMAIN": "example.com",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_production_contract_accepts_valid_configuration(monkeypatch):
    _set_valid_production(monkeypatch)
    assert all(status == "OK" or not critical for _, status, critical in validate_production_config())


def test_production_contract_rejects_placeholder_secret(monkeypatch):
    _set_valid_production(monkeypatch)
    monkeypatch.setenv("EOS_SECRET_KEY", "CHANGE_ME_" + "A" * 64)
    checks = validate_production_config()
    assert any(name == "EOS_SECRET_KEY" and status == "INVALID FORMAT" for name, status, _ in checks)


def test_production_contract_rejects_test_stripe_key(monkeypatch):
    _set_valid_production(monkeypatch)
    monkeypatch.setenv("EOS_STRIPE_SECRET_KEY", "sk_test_123456")
    checks = validate_production_config()
    assert any(name == "EOS_STRIPE_SECRET_KEY" and status == "INVALID FORMAT" for name, status, _ in checks)


def test_production_contract_rejects_unsupported_jwt_algorithm(monkeypatch):
    _set_valid_production(monkeypatch)
    monkeypatch.setenv("EOS_ALGORITHM", "none")
    checks = validate_production_config()
    assert any(name == "EOS_ALGORITHM" and status == "INVALID FORMAT" for name, status, _ in checks)


def test_production_contract_requires_rs256_keypair(monkeypatch):
    _set_valid_production(monkeypatch)
    monkeypatch.setenv("EOS_ALGORITHM", "RS256")
    monkeypatch.delenv("EOS_JWT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("EOS_JWT_PUBLIC_KEY", raising=False)
    checks = validate_production_config()
    assert any(name == "EOS_JWT_PRIVATE_KEY" and status == "MISSING" for name, status, _ in checks)
    assert any(name == "EOS_JWT_PUBLIC_KEY" and status == "MISSING" for name, status, _ in checks)


@pytest.mark.parametrize(
    "cors",
    [
        '["http://app.example.com"]',
        '["https://app.example.com", "http://admin.example.com"]',
    ],
)
def test_production_contract_rejects_non_https_cors(monkeypatch, cors):
    _set_valid_production(monkeypatch)
    monkeypatch.setenv("EOS_CORS_ORIGINS", cors)
    checks = validate_production_config()
    assert any(name == "EOS_CORS_ORIGINS" and status == "INVALID FORMAT" for name, status, _ in checks)
