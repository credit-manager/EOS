"""Production configuration validator.

Security-critical production settings fail closed at startup, including the
PostgreSQL role properties required for RLS to be effective.
"""
import os
import re
import sys


class ProductionConfigError(Exception):
    pass


def _check_database_role() -> tuple[str, str, bool]:
    """Ensure the application role cannot bypass PostgreSQL RLS."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.rolsuper, r.rolbypassrls,
                           (current_database() = pg_get_userbyid(d.datdba)) AS is_owner
                    FROM pg_roles r CROSS JOIN pg_database d
                    WHERE r.rolname = current_user AND d.datname = current_database()
                """)
                row = cur.fetchone()
        finally:
            conn.close()
        if not row:
            return ("DATABASE_ROLE_RLS_SAFE", "INVALID", True)
        if any(bool(value) for value in row):
            return ("DATABASE_ROLE_RLS_SAFE", "INVALID: superuser/bypassrls/owner", True)
        return ("DATABASE_ROLE_RLS_SAFE", "OK", True)
    except Exception:
        # Do not permit a production deployment to silently skip this control.
        return ("DATABASE_ROLE_RLS_SAFE", "UNVERIFIED", True)


def validate_production_config() -> list[tuple[str, str, bool]]:
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

    check("EOS_AUTH_MODE", os.getenv("EOS_AUTH_MODE", ""), r"^production$", True)
    check("EOS_ENVIRONMENT", os.getenv("EOS_ENVIRONMENT", ""), r"^production$", True)
    check("EOS_SECRET_KEY", os.getenv("EOS_SECRET_KEY", ""), r"^.{32,}$", True)
    check("DATABASE_URL", os.getenv("DATABASE_URL", ""), r"^postgresql://.{10,}$", True)
    if os.getenv("DATABASE_URL", "").startswith("postgresql://"):
        checks.append(_check_database_role())
    check("EOS_2FA_ENCRYPTION_KEY", os.getenv("EOS_2FA_ENCRYPTION_KEY", ""), r"^.{44}$", True)

    email_provider = os.getenv("EOS_EMAIL_PROVIDER", "")
    check("EOS_EMAIL_PROVIDER", email_provider, r"^smtp$", True)
    if email_provider == "smtp":
        for name in ("EOS_SMTP_HOST", "EOS_SMTP_USERNAME", "EOS_SMTP_PASSWORD", "EOS_FROM_EMAIL"):
            check(name, os.getenv(name, ""), critical=True)

    payment_mode = os.getenv("EOS_PAYMENT_MODE", "")
    check("EOS_PAYMENT_MODE", payment_mode, r"^(disabled|stripe)$", True)
    if payment_mode == "stripe":
        check("EOS_STRIPE_SECRET_KEY", os.getenv("EOS_STRIPE_SECRET_KEY", ""), r"^sk_live_.{10,}$", True)

    check("EOS_FRONTEND_URL", os.getenv("EOS_FRONTEND_URL", ""), r"^https://", True)
    check("EOS_CORS_ORIGINS", os.getenv("EOS_CORS_ORIGINS", ""), critical=True)
    check("EOS_ALLOWED_HOSTS", os.getenv("EOS_ALLOWED_HOSTS", ""), critical=True)
    if "*" in os.getenv("EOS_ALLOWED_HOSTS", ""):
        checks.append(("EOS_ALLOWED_HOSTS_WILDCARD", "INVALID", True))
    check("EOS_TRUSTED_HOSTS_ENABLED", os.getenv("EOS_TRUSTED_HOSTS_ENABLED", ""), r"^true$", True)
    check("EOS_DISABLE_DOCS", os.getenv("EOS_DISABLE_DOCS", ""), r"^true$", True)
    check("EOS_RATE_LIMIT_FAIL_CLOSED", os.getenv("EOS_RATE_LIMIT_FAIL_CLOSED", ""), r"^true$", True)
    check("EOS_TRUSTED_PROXIES", os.getenv("EOS_TRUSTED_PROXIES", ""), critical=True)
    check("POSTGRES_USER", os.getenv("POSTGRES_USER", ""), critical=True)
    check("POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""), critical=True)
    check("POSTGRES_DB", os.getenv("POSTGRES_DB", ""), critical=True)
    check("DOMAIN", os.getenv("DOMAIN", ""), r"^https://", True)
    check("EOS_METRICS_TOKEN", os.getenv("EOS_METRICS_TOKEN", ""), r"^.{32,}$", True)
    check("EOS_HEALTH_TOKEN", os.getenv("EOS_HEALTH_TOKEN", ""), r"^.{32,}$", True)
    check("EOS_RUNTIME_SCHEMA", os.getenv("EOS_RUNTIME_SCHEMA", "false"), r"^false$", True)
    if os.getenv("EOS_OTEL_ENABLED", "false").lower() == "true":
        check("OTEL_EXPORTER_OTLP_ENDPOINT", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""), r"^https://", True)
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
