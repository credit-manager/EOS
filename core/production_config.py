"""Production configuration validator.

Production startup must fail closed when security-critical controls are missing.
"""
import os
import re
import sys
from typing import List, Tuple


class ProductionConfigError(Exception):
    pass


def validate_production_config() -> List[Tuple[str, str, bool]]:
    checks = []

    def check(name: str, value: str, pattern: str = None, critical: bool = True):
        if not value:
            checks.append((name, "MISSING", critical))
            return False
        if pattern and not re.match(pattern, value):
            checks.append((name, "INVALID FORMAT", critical))
            return False
        checks.append((name, "OK", critical))
        return True

    check("EOS_AUTH_MODE", os.getenv("EOS_AUTH_MODE", ""), r"^production$", True)
    check("EOS_ENVIRONMENT", os.getenv("EOS_ENVIRONMENT", ""), r"^production$", True)
    check("EOS_SECRET_KEY", os.getenv("EOS_SECRET_KEY", ""), r"^.{32,}$", True)
    check("DATABASE_URL", os.getenv("DATABASE_URL", ""), r"^postgresql://.{10,}$", True)
    check("EOS_2FA_ENCRYPTION_KEY", os.getenv("EOS_2FA_ENCRYPTION_KEY", ""), r"^.{44}$", True)

    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "")
    check("EOS_EMAIL_PROVIDER", email_provider, r"^smtp$", True)
    if email_provider == "smtp":
        check("EOS_SMTP_HOST", os.getenv("EOS_SMTP_HOST", ""), critical=True)
        check("EOS_SMTP_USERNAME", os.getenv("EOS_SMTP_USERNAME", ""), critical=True)
        check("EOS_SMTP_PASSWORD", os.getenv("EOS_SMTP_PASSWORD", ""), critical=True)
        check("EOS_FROM_EMAIL", os.getenv("EOS_FROM_EMAIL", ""), critical=True)

    payment_mode = os.getenv("EOS_PAYMENT_MODE", "stripe")
    check("EOS_PAYMENT_MODE", payment_mode, r"^(stripe)$", True)
    if payment_mode == "stripe":
        check("EOS_STRIPE_SECRET_KEY", os.getenv("EOS_STRIPE_SECRET_KEY", ""), r"^sk_live_.{10,}$", True)

    check("EOS_FRONTEND_URL", os.getenv("EOS_FRONTEND_URL", ""), r"^https://", True)
    check("EOS_CORS_ORIGINS", os.getenv("EOS_CORS_ORIGINS", ""), critical=True)
    check("EOS_ALLOWED_HOSTS", os.getenv("EOS_ALLOWED_HOSTS", ""), critical=True)
    check("EOS_TRUSTED_HOSTS_ENABLED", os.getenv("EOS_TRUSTED_HOSTS_ENABLED", ""), r"^true$", True)
    check("EOS_DISABLE_DOCS", os.getenv("EOS_DISABLE_DOCS", ""), r"^true$", True)
    check("EOS_RATE_LIMIT_FAIL_CLOSED", os.getenv("EOS_RATE_LIMIT_FAIL_CLOSED", ""), r"^true$", True)
    check("EOS_TRUSTED_PROXIES", os.getenv("EOS_TRUSTED_PROXIES", ""), critical=True)

    check("POSTGRES_USER", os.getenv("POSTGRES_USER", ""), critical=True)
    check("POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""), critical=True)
    check("POSTGRES_DB", os.getenv("POSTGRES_DB", ""), critical=True)
    check("DOMAIN", os.getenv("DOMAIN", ""), r"^https://", True)
    return checks


def run_validation():
    print("=" * 60)
    print("  EOS PRODUCTION CONFIGURATION VALIDATOR")
    print("=" * 60)
    try:
        checks = validate_production_config()
    except Exception as exc:
        print(f"\n  FATAL: {exc}")
        sys.exit(1)

    critical_failures = 0
    for name, status, is_critical in checks:
        if status == "OK":
            print(f"  OK    {name}")
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
    print("  ALL CHECKS PASSED — production configuration is valid")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    run_validation()
