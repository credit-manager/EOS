"""Production configuration validator; unsafe development defaults fail closed."""

import os
import re
import sys
from typing import List, Tuple
from urllib.parse import urlparse

from core.runtime_config import RuntimeConfigurationError, allowed_hosts, cors_origins


class ProductionConfigError(Exception):
    pass


def validate_production_config() -> List[Tuple[str, str, bool]]:
    checks = []

    def check(name: str, value: str, pattern: str = None, critical: bool = True):
        if not value:
            checks.append((name, "MISSING", critical))
            return False
        if pattern and not re.fullmatch(pattern, value):
            checks.append((name, "INVALID FORMAT", critical))
            return False
        checks.append((name, "OK", critical))
        return True

    check("EOS_AUTH_MODE", os.getenv("EOS_AUTH_MODE", ""), r"production", critical=True)

    secret_key = os.getenv("EOS_SECRET_KEY", "")
    secret_ok = check("EOS_SECRET_KEY", secret_key, r".{32,}", critical=True)
    if secret_ok and re.search(r"(?:CHANGE_ME|test_secret_key|example|placeholder)", secret_key, re.IGNORECASE):
        checks.append(("EOS_SECRET_KEY", "INVALID FORMAT", True))

    check("DATABASE_URL", os.getenv("DATABASE_URL", ""), r"postgresql(?:\+\w+)?://.{10,}", critical=True)

    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "")
    check("EOS_EMAIL_PROVIDER", email_provider, r"smtp", critical=True)
    if email_provider == "smtp":
        check("EOS_SMTP_HOST", os.getenv("EOS_SMTP_HOST", ""), critical=True)
        check("EOS_SMTP_USERNAME", os.getenv("EOS_SMTP_USERNAME", ""), critical=True)
        check("EOS_SMTP_PASSWORD", os.getenv("EOS_SMTP_PASSWORD", ""), critical=True)
        check("EOS_FROM_EMAIL", os.getenv("EOS_FROM_EMAIL", ""), critical=True)

    payment_mode = os.getenv("EOS_PAYMENT_MODE", "")
    check("EOS_PAYMENT_MODE", payment_mode, r"stripe", critical=True)
    if payment_mode == "stripe":
        stripe_key = os.getenv("EOS_STRIPE_SECRET_KEY", "")
        check("EOS_STRIPE_SECRET_KEY", stripe_key, r"sk_live_.+", critical=True)
        if stripe_key and stripe_key.startswith("sk_test"):
            checks.append(("EOS_STRIPE_SECRET_KEY", "INVALID FORMAT", True))

    frontend_url = os.getenv("EOS_FRONTEND_URL", "")
    check("EOS_FRONTEND_URL", frontend_url, r"https://.+", critical=True)
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

    check("POSTGRES_USER", os.getenv("POSTGRES_USER", ""), critical=True)
    check("POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""), critical=True)
    check("POSTGRES_DB", os.getenv("POSTGRES_DB", ""), critical=True)
    check("DOMAIN", os.getenv("DOMAIN", ""), critical=True)
    return checks


def run_validation():
    print("=" * 60)
    print("  P62 PRODUCTION CONFIGURATION VALIDATOR")
    print("=" * 60)
    try:
        checks = validate_production_config()
    except Exception as e:
        print("\n  FATAL: production configuration could not be validated")
        print(f"  Reason: {type(e).__name__}")
        sys.exit(1)
    critical_failures = 0
    warnings = 0
    for name, status, is_critical in checks:
        if status == "OK":
            print(f"  OK    {name}")
        elif status.startswith("WARNING"):
            print(f"  WARN  {name}: {status}")
            warnings += 1
            if is_critical:
                critical_failures += 1
        else:
            tag = "CRITICAL" if is_critical else "OPTIONAL"
            print(f"  {tag}  {name}: {status}")
            if is_critical:
                critical_failures += 1
    print("\n" + "=" * 60)
    if critical_failures:
        print(f"  FAILED: {critical_failures} critical settings missing/invalid")
        print("  Fix the above issues before deploying to production.")
        print("=" * 60)
        sys.exit(1)
    print("  Production configuration contract PASSED")
    print("  Deployment infrastructure and external provider checks remain required.")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    run_validation()
