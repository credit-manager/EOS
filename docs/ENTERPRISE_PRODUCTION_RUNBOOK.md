# EOS Enterprise Production Runbook

This runbook separates controls that can be verified in source/CI from controls that require evidence from the deployed infrastructure.

## 1. PostgreSQL tenant isolation

The application refuses a production connection when its PostgreSQL role is a superuser, has `BYPASSRLS`, or owns the database. Use a dedicated application role and a separate migration/administration role.

Required evidence:

```sql
SELECT current_user,
       rolsuper,
       rolbypassrls,
       pg_get_userbyid((SELECT datdba FROM pg_database WHERE datname=current_database())) AS database_owner
FROM pg_roles
WHERE rolname=current_user;
```

All three security conditions must be false/different before production traffic is enabled.

## 2. Webhook egress

Application-level SSRF validation is required, but it is not a substitute for network egress controls. Production should route webhook traffic through an egress proxy/firewall with an explicit allow policy and deny RFC1918, loopback, link-local, metadata-service and other non-public destinations.

Record the proxy/firewall policy version and a successful negative test as release evidence.

## 3. Object storage

Use tenant-scoped object keys/prefixes and server-side authorization on every read, write, delete, and signed-URL operation. Never expose a bucket credential to the browser. Record a cross-tenant negative test for every storage API family.

## 4. Availability

Production requires multiple application instances behind a health-checked load balancer. PostgreSQL and Redis, when used, require managed or self-hosted HA with documented failover behavior.

Use `/health/live` for process liveness and `/health/ready` for load-balancer readiness. `/health/full` exposes operational telemetry and therefore requires `X-Health-Token` in production. Store `EOS_HEALTH_TOKEN` as a secret and never put it in source control.

Record:
- node count and zones
- health-check configuration
- failover test date
- expected and measured recovery time

## 5. Backup and disaster recovery

Enable PostgreSQL point-in-time recovery and off-host backup retention. Perform a restore drill before the first production release and after material infrastructure changes.

Record:
- backup retention
- recovery window
- RPO target and measured RPO
- RTO target and measured RTO
- restore drill result
- cross-region strategy where required by the SLA

## 6. Observability

Production must provide metrics, structured logs, distributed traces, and actionable alerts. Define SLIs/SLOs and error budgets for availability, latency, error rate, queue age, database health, and webhook delivery.

The service exposes a protected Prometheus metrics endpoint and request-correlated structured logs. Distributed tracing and SLO evidence remain deployment gates until verified.

## 7. Supply-chain security

For each release retain:
- Python SBOM
- frontend dependency lockfile/SBOM
- container SBOM
- container vulnerability scan
- image signature/provenance
- dependency vulnerability report
- immutable GitHub Actions references

Never use credentials or default passwords in production configuration.

## 8. Financial correctness

Before production sign-off, execute end-to-end accounting acceptance tests covering double-entry posting, trial balance, P&L, balance sheet, cash flow, fiscal periods, period close/reopen, opening balances, dimensions, tax, multi-currency, retained earnings, and audit-safe corrections.

Security CI passing does not constitute financial correctness certification.

## 9. ERP compiler safety

Generated ERP definitions must pass an intermediate representation/schema validator, dependency graph validation, authorization policy validation, migration preview, destructive-change detection, generated test validation, API/UI contract validation, approval/versioning, and rollback checks before deployment.

## 10. Release gate

Run:

```text
python scripts/verify_enterprise_readiness.py
```

The command intentionally fails until live evidence variables are supplied. This is deliberate: missing production evidence must not be reported as green.
