"""Fail-closed production readiness checks that require real deployment evidence.

Usage in a production environment:
    python scripts/verify_enterprise_readiness.py

This intentionally does not manufacture evidence for HA, backups, storage,
network egress, tracing, or compliance. Those checks require live infrastructure
and are reported as FAIL until the operator provides explicit evidence variables.
"""

import os
import sys
from urllib.parse import urlparse


REQUIRED_TRUE = {
    "EOS_AUTH_MODE": "production",
    "EOS_ENVIRONMENT": "production",
    "EOS_DISABLE_DOCS": "true",
    "EOS_TRUSTED_HOSTS_ENABLED": "true",
    "EOS_RATE_LIMIT_FAIL_CLOSED": "true",
}

EVIDENCE_FLAGS = {
    "EOS_RLS_ROLE_VERIFIED": "PostgreSQL app role is non-owner, non-superuser and non-BYPASSRLS",
    "EOS_WEBHOOK_EGRESS_CONTROL_VERIFIED": "Webhook egress is restricted by network/proxy policy",
    "EOS_OBJECT_STORAGE_ISOLATION_VERIFIED": "Object storage is tenant-isolated and access-controlled",
    "EOS_HA_VERIFIED": "Application HA/load balancing is deployed",
    "EOS_DB_HA_VERIFIED": "PostgreSQL HA/failover is deployed",
    "EOS_REDIS_HA_VERIFIED": "Redis HA/failover is deployed where Redis is used",
    "EOS_PITR_VERIFIED": "PostgreSQL PITR backups are enabled",
    "EOS_RESTORE_DRILL_VERIFIED": "A recent restore drill succeeded",
    "EOS_RTO_RPO_VERIFIED": "RTO/RPO targets are documented and tested",
    "EOS_OTEL_VERIFIED": "Distributed tracing is deployed",
    "EOS_SLO_VERIFIED": "SLI/SLO/error-budget alerting is deployed",
    "EOS_SBOM_VERIFIED": "SBOM is generated and retained for the release",
    "EOS_IMAGE_SCAN_VERIFIED": "Production image scanning passed",
    "EOS_IMAGE_SIGNING_VERIFIED": "Production image provenance/signing is verified",
    "EOS_COMPLIANCE_EVIDENCE_VERIFIED": "Required compliance controls have evidence",
    "EOS_DATA_RESIDENCY_VERIFIED": "Data residency/retention/DSAR controls are verified",
}


def _ok(name: str, value: str | None) -> bool:
    return value is not None and value.strip().lower() == "true"


def main() -> int:
    failures: list[str] = []
    print("EOS ENTERPRISE PRODUCTION READINESS")
    print("=" * 48)

    for name, expected in REQUIRED_TRUE.items():
        actual = os.getenv(name, "")
        if actual.lower() != expected:
            failures.append(f"{name} must be {expected!r}")
            print(f"FAIL  {name}: {actual or 'MISSING'}")
        else:
            print(f"OK    {name}")

    secret = os.getenv("EOS_SECRET_KEY", "")
    if len(secret) < 32:
        failures.append("EOS_SECRET_KEY must contain at least 32 characters")
        print("FAIL  EOS_SECRET_KEY")
    else:
        print("OK    EOS_SECRET_KEY")

    database_url = os.getenv("DATABASE_URL", "")
    parsed = urlparse(database_url)
    if parsed.scheme != "postgresql" or not parsed.hostname:
        failures.append("DATABASE_URL must point to PostgreSQL")
        print("FAIL  DATABASE_URL")
    else:
        print("OK    DATABASE_URL")

    allowed_hosts = [h.strip() for h in os.getenv("EOS_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if not allowed_hosts or "*" in allowed_hosts:
        failures.append("EOS_ALLOWED_HOSTS must be explicit; wildcard is forbidden")
        print("FAIL  EOS_ALLOWED_HOSTS")
    else:
        print("OK    EOS_ALLOWED_HOSTS")

    for name, description in EVIDENCE_FLAGS.items():
        if _ok(name, os.getenv(name)):
            print(f"OK    {name}")
        else:
            failures.append(f"{name}: {description}")
            print(f"FAIL  {name}")

    print("=" * 48)
    if failures:
        print(f"FAILED: {len(failures)} production gate(s) remain")
        for item in failures:
            print(f" - {item}")
        return 1
    print("ALL ENTERPRISE PRODUCTION GATES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
