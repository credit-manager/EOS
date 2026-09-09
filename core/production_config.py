"""Fail-closed production configuration validation."""

import os
import re
import sys
from typing import List, Tuple
from urllib.parse import urlparse

from core.production_auth import SUPPORTED_JWT_ALGORITHMS
from core.runtime_config import RuntimeConfigurationError, allowed_hosts, cors_origins


class ProductionConfigError(Exception):
    """Raised when production configuration is invalid."""


def _check(checks, name: str, value: str, pattern: str | None = None) -> bool:
    if not value:
        checks.append((name, "MISSING", True))
        return False
    if pattern and not re.fullmatch(pattern, value):
        checks.append((name, "INVALID FORMAT", True))
        return False
    checks.append((name, "OK", True))
    return True


def validate_production_config() -> List[Tuple[str, str, bool]]:
    checks: List[Tuple[str, str, bool]] = []

    _check(checks, "EOS_AUTH_MODE", os.getenv("EOS_AUTH_MODE", ""), r"production")

    secret_key = os.getenv("EOS_SECRET_KEY", "")
    if _check(checks, "EOS_SECRET_KEY", secret_key, r".{32,}") and re.search(
        r"(?:CHANGE_ME|test_secret_key|example|placeholder)", secret_key, re.IGNORECASE
    ):
        checks.append(("EOS_SECRET_KEY", "INVALID FORMAT", True))

    algorithm = os.getenv("EOS_ALGORITHM", "HS256").strip().upper() or "HS256"
    if algorithm not in SUPPORTED_JWT_ALGORITHMS:
        checks.append(("EOS_ALGORITHM", "INVALID FORMAT", True))
    else:
        checks.append(("EOS_ALGORITHM", "OK", True))

    if algorithm == "RS256":
        private_key = os.getenv("EOS_JWT_PRIVATE_KEY", "").strip()
        public_key = os.getenv("EOS_JWT_PUBLIC_KEY", "").strip()
        private_ok = _check(checks, "EOS_JWT_PRIVATE_KEY", private_key)
        public_ok = _check(checks, "EOS_JWT_PUBLIC_KEY", public_key)
        if private_ok and "BEGIN PRIVATE KEY" not in private_key and "BEGIN RSA PRIVATE KEY" not in private_key:
            checks.append(("EOS_JWT_PRIVATE_KEY", "INVALID FORMAT", True))
        if public_ok and "BEGIN PUBLIC KEY" not in public_key and "BEGIN RSA PUBLIC KEY" not in public_key:
            checks.append(("EOS_JWT_PUBLIC_KEY", "INVALID FORMAT", True))

    issuer = os.getenv("EOS_JWT_ISSUER", "eos-dbp").strip()
    audience = os.getenv("EOS_JWT_AUDIENCE", "eos-api").strip()
    _check(checks, "EOS_JWT_ISSUER", issuer, r"[^\s]{1,200}")
    _check(checks, "EOS_JWT_AUDIENCE", audience, r"[^\s]{1,200}")

    _check(checks, "DATABASE_URL", os.getenv("DATABASE_URL", ""), r"postgresql(?:\+\w+)?://.{10,}")

    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "")
    _check(checks, "EOS_EMAIL_PROVIDER", email_provider, r"smtp")
    if email_provider == "smtp":
        for name in ("EOS_SMTP_HOST", "EOS_SMTP_USERNAME", "EOS_SMTP_PASSWORD", "EOS_FROM_EMAIL"):
            _check(checks, name, os.getenv(name, ""))

    payment_mode = os.getenv("EOS_PAYMENT_MODE", "")
    _check(checks, "EOS_PAYMENT_MODE", payment_mode, r"stripe")
    if payment_mode == "stripe":
        stripe_key = os.getenv("EOS_STRIPE_SECRET_KEY", "")
        if _check(checks, "EOS_STRIPE_SECRET_KEY", stripe_key, r"sk_live_.+") and re.search(
            r"(?:test|example|placeholder|contract|change_me)", stripe_key, re.IGNORECASE
        ):
            checks.append(("EOS_STRIPE_SECRET_KEY", "INVALID FORMAT", True))

    frontend_url = os.getenv("EOS_FRONTEND_URL", "")
    _check(checks, "EOS_FRONTEND_URL", frontend_url, r"https://[^\s]+")
    if frontend_url:
        parsed = urlparse(frontend_url)
        if parsed.scheme != "https" or not parsed.netloc:
            checks.append(("EOS_FRONTEND_URL", "INVALID FORMAT", True))

    cors_value = os.getenv("EOS_CORS_ORIGINS", "")
    if not cors_value:
        checks.append(("EOS_CORS_ORIGINS", "MISSING", True))
    else:
        try:
            origins = cors_origins()
            if any(urlparse(origin).scheme != "https" or not urlparse(origin).netloc for origin in origins):
                raise RuntimeConfigurationError("production CORS origins must be HTTPS")
            checks.append(("EOS_CORS_ORIGINS", "OK", True))
        except RuntimeConfigurationError:
            checks.append(("EOS_CORS_ORIGINS", "INVALID FORMAT", True))

    hosts_value = os.getenv("EOS_ALLOWED_HOSTS", "")
    if not hosts_value:
        checks.append(("EOS_ALLOWED_HOSTS", "MISSING", True))
    else:
        try:
            hosts = allowed_hosts()
            if any(not host or host == "*" or host.startswith(".") for host in hosts):
                raise RuntimeConfigurationError("invalid trusted host")
            checks.append(("EOS_ALLOWED_HOSTS", "OK", True))
        except RuntimeConfigurationError:
            checks.append(("EOS_ALLOWED_HOSTS", "INVALID FORMAT", True))

    for name in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DOMAIN"):
        _check(checks, name, os.getenv(name, ""))

    return checks


def run_validation() -> None:
    print("=" * 60)
    print("  EOS PRODUCTION CONFIGURATION VALIDATOR")
    print("=" * 60)
    try:
        checks = validate_production_config()
    except Exception as exc:
        print("\n  FATAL: production configuration could not be validated")
        print(f"  Reason: {type(exc).__name__}")
        raise SystemExit(1) from exc

    critical_failures = 0
    for name, status, critical in checks:
        if status == "OK":
            print(f"  OK    {name}")
        else:
            tag = "CRITICAL" if critical else "OPTIONAL"
            print(f"  {tag}  {name}: {status}")
            if critical:
                critical_failures += 1

    print("\n" + "=" * 60)
    if critical_failures:
        print(f"  FAILED: {critical_failures} critical settings missing/invalid")
        print("  Fix the above issues before deploying to production.")
        print("=" * 60)
        raise SystemExit(1)
    print("  Production configuration contract PASSED")
    print("  External infrastructure/provider verification remains required.")
    print("=" * 60)


if __name__ == "__main__":
    run_validation()
