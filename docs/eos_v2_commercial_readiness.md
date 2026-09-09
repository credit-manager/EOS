# EOS DBP v2 Commercial Readiness

## Release gates

1. Identity: asymmetric RS256/OIDC-compatible validation, JWKS publication, overlapping keys during rotation, short-lived access tokens, issuer/audience validation in production.
2. Observability: request IDs, structured logs, Prometheus metrics, tracing, health/readiness, alert thresholds and dashboards.
3. Frontend: generated from the same metadata contract; no duplicated business schema; tenant-aware routing and permission-aware UI.
4. Performance: repeatable load tests for auth, metadata, dynamic records and representative ERP transactions; define p95/p99 SLOs and failure thresholds.
5. Resilience: automated backups, encrypted storage, restore verification, RPO/RTO targets, quarterly disaster-recovery rehearsal.
6. Security: dependency/SAST scan, secrets audit, tenant-isolation regression suite, rate limits, headers, TLS, audit trail, threat model and release checklist.
7. Delivery: staging deploy, smoke tests, migration rehearsal, canary, rollback procedure and post-deploy verification.
8. Construction/real estate: end-to-end flows for land acquisition, development projects, units, contracts, purchasing, inventory, workforce/project costs and accounting posting.
9. Legacy: freeze legacy writes, backup, row-count/integrity reconciliation, staged migration, dual-read validation where required, rollback rehearsal, then read-only/archive/decommission.

## Non-negotiable rule

A release is not Commercial GA until every gate is evidenced by automated tests or an operational rehearsal. CI passing alone is insufficient.
