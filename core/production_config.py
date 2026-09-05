"""Production configuration validator; unsafe development defaults fail closed."""
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

    check("EOS_AUTH_MODE", os.getenv("EOS_AUTH_MODE", ""), r"^production$", critical=True)
    check("EOS_SECRET_KEY", os.getenv("EOS_SECRET_KEY", ""), r"^.{32,}$", critical=True)
    check("DATABASE_URL", os.getenv("DATABASE_URL", ""), r"^postgresql(?:\+\w+)?://.{10,}$", critical=True)

    # Development-only console mail is never accepted in production.
    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "")
    check("EOS_EMAIL_PROVIDER", email_provider, r"^smtp$", critical=True)
    if email_provider == "smtp":
        check("EOS_SMTP_HOST", os.getenv("EOS_SMTP_HOST", ""), critical=True)
        check("EOS_SMTP_USERNAME", os.getenv("EOS_SMTP_USERNAME", ""), critical=True)
        check("EOS_SMTP_PASSWORD", os.getenv("EOS_SMTP_PASSWORD", ""), critical=True)
        check("EOS_FROM_EMAIL", os.getenv("EOS_FROM_EMAIL", ""), critical=True)

    # Test payment mode is never accepted in production.
    payment_mode = os.getenv("EOS_PAYMENT_MODE", "")
    check("EOS_PAYMENT_MODE", payment_mode, r"^stripe$", critical=True)
    if payment_mode == "stripe":
        stripe_key = os.getenv("EOS_STRIPE_SECRET_KEY", "")
        check("EOS_STRIPE_SECRET_KEY", stripe_key, critical=True)
        if stripe_key and stripe_key.startswith("sk_test"):
            checks.append(("EOS_STRIPE_SECRET_KEY", "WARNING: Using test key in production!", True))

    check("EOS_FRONTEND_URL", os.getenv("EOS_FRONTEND_URL", ""), critical=True)
    check("EOS_CORS_ORIGINS", os.getenv("EOS_CORS_ORIGINS", ""), critical=True)
    check("EOS_ALLOWED_HOSTS", os.getenv("EOS_ALLOWED_HOSTS", ""), critical=True)
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
        print(f"\n  FATAL: {e}")
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
    print("  ALL CHECKS PASSED — Ready for production deployment")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    run_validation()
