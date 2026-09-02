"""
P62 Production Configuration Validator.
Checks all required settings before starting in production mode.
Blocks startup if critical settings are missing.
"""
import os
import re
import sys


class ProductionConfigError(Exception):
    pass


def validate_production_config() -> list[tuple[str, str, bool]]:
    """
    Validate all production configuration.
    Returns list of (setting, status, is_critical).
    Raises ProductionConfigError if critical settings are missing.
    """
    checks = []

    def check(name: str, value: str, pattern: str | None = None, critical: bool = True):
        if not value:
            checks.append((name, "MISSING", critical))
            return False
        if pattern and not re.match(pattern, value):
            checks.append((name, "INVALID FORMAT", critical))
            return False
        checks.append((name, "OK", critical))
        return True

    # Auth mode MUST be production
    auth_mode = os.getenv("EOS_AUTH_MODE", "")
    check("EOS_AUTH_MODE", auth_mode, r"^production$", critical=True)

    # Secret key — strong and long
    secret = os.getenv("EOS_SECRET_KEY", "")
    check("EOS_SECRET_KEY", secret, r"^.{32,}$", critical=True)

    # Database URL
    db_url = os.getenv("DATABASE_URL", "")
    check("DATABASE_URL", db_url, r"^postgresql://.{10,}$", critical=True)

    # Email provider
    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "console")
    check("EOS_EMAIL_PROVIDER", email_provider, r"^(smtp|console)$", critical=False)

    if email_provider == "smtp":
        check("EOS_SMTP_HOST", os.getenv("EOS_SMTP_HOST", ""), critical=True)
        check("EOS_SMTP_USERNAME", os.getenv("EOS_SMTP_USERNAME", ""), critical=True)
        check("EOS_SMTP_PASSWORD", os.getenv("EOS_SMTP_PASSWORD", ""), critical=True)
        check("EOS_FROM_EMAIL", os.getenv("EOS_FROM_EMAIL", ""), critical=True)

    # Stripe
    payment_mode = os.getenv("EOS_PAYMENT_MODE", "test")
    check("EOS_PAYMENT_MODE", payment_mode, r"^(test|stripe)$", critical=False)

    if payment_mode == "stripe":
        stripe_key = os.getenv("EOS_STRIPE_SECRET_KEY", "")
        check("EOS_STRIPE_SECRET_KEY", stripe_key, critical=True)
        if stripe_key and stripe_key.startswith("sk_test"):
            checks.append(("EOS_STRIPE_SECRET_KEY", "WARNING: Using test key in production!", False))

    # Frontend URL
    frontend = os.getenv("EOS_FRONTEND_URL", "")
    check("EOS_FRONTEND_URL", frontend, critical=True)

    # CORS
    cors = os.getenv("EOS_CORS_ORIGINS", "")
    check("EOS_CORS_ORIGINS", cors, critical=True)

    # Allowed hosts
    hosts = os.getenv("EOS_ALLOWED_HOSTS", "")
    check("EOS_ALLOWED_HOSTS", hosts, critical=True)

    # Postgres
    check("POSTGRES_USER", os.getenv("POSTGRES_USER", ""), critical=True)
    check("POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""), critical=True)
    check("POSTGRES_DB", os.getenv("POSTGRES_DB", ""), critical=True)

    # Domain
    check("DOMAIN", os.getenv("DOMAIN", ""), critical=True)

    return checks


def run_validation():
    """Run validation and print results. Exits with code 1 if critical failures."""
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
        else:
            tag = "CRITICAL" if is_critical else "OPTIONAL"
            print(f"  {tag}  {name}: {status}")
            if is_critical:
                critical_failures += 1

    print("\n" + "=" * 60)
    if critical_failures > 0:
        print(f"  FAILED: {critical_failures} critical settings missing")
        print("  Fix the above issues before deploying to production.")
        print("=" * 60)
        sys.exit(1)
    else:
        print("  ALL CHECKS PASSED — Ready for production deployment")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    run_validation()
