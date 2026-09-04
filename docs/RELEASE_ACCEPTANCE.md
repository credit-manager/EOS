# EOS Release Acceptance Gate

This checklist is intentionally evidence-driven. A source-code change cannot manufacture infrastructure evidence.

## Code/CI gates

- [x] Application imports and Python syntax compile.
- [x] Security regression suite passes.
- [x] Frontend lint, tests and build pass.
- [x] Backend quality/security scanners pass.
- [x] Alembic upgrade/check gate exists.
- [x] RLS CI negative test uses a non-owner, non-superuser, non-BYPASSRLS role.
- [x] Frontend dependency lockfile is committed.
- [x] Docker build consumes the committed lockfile.
- [x] Container HIGH/CRITICAL scan and container SBOM workflow exist.
- [x] API contract checker exists.
- [x] Payment critical writes use idempotency and transactional outbox primitives.

## Production evidence gates

These must be completed on the actual deployment before declaring GA:

- [ ] Dedicated PostgreSQL application role proven non-owner/non-superuser/non-BYPASSRLS.
- [ ] Webhook egress proxy/firewall policy and negative SSRF/egress test recorded.
- [ ] Object-storage tenant isolation and cross-tenant negative tests recorded.
- [ ] Multiple application instances/load balancer failover test recorded.
- [ ] PostgreSQL HA/failover test recorded.
- [ ] Redis HA/failover test recorded when Redis is used.
- [ ] PITR backup retention and restore drill recorded.
- [ ] RTO/RPO measured and accepted against SLA.
- [ ] OpenTelemetry collector deployed and trace observed end-to-end.
- [ ] SLI/SLO/error-budget alerts deployed and tested.
- [ ] Release Python/frontend/container SBOMs retained.
- [ ] Production image scan passed for the exact released image digest.
- [ ] Production image provenance/signing verified for the exact released artifact.
- [ ] Compliance controls/evidence completed for target jurisdictions.
- [ ] Data residency, retention, DSAR and legal-hold controls verified.
- [ ] Full financial acceptance suite passed by accounting owner.
- [ ] ERP generation/compiler safety pipeline passed for representative industry packs.
- [ ] Critical-write idempotency/outbox coverage audited across invoices, orders, journals, workflows, webhooks, AI and ERP generation.
- [ ] Background jobs, cache/search and concurrency controls have tenant-isolation and load evidence.

## Rule

Do not set any production evidence environment variable merely to make the verifier pass. Each variable must correspond to a retained artifact, test result, infrastructure configuration, or approved control record.
