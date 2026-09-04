# EOS P0 / Enterprise Readiness Tracker

**Last reviewed:** 2026-09-04  
**Branch:** `custom-erp-system-for-companies-24152`  
**Policy:** a control is GREEN only when the implementation and its verification evidence both pass. Missing production evidence is FAIL/CLOSED-GATE, never assumed green.

## 1. P0 Security — GREEN in source/CI

- [x] AI Composer tenant/IDOR isolation
- [x] 2FA durable encryption key enforcement
- [x] Rate limiter trusted-proxy and fail-closed behavior
- [x] Dynamic CRUD tenant isolation and SQL identifier validation
- [x] M2M tenant isolation for target and junction tables
- [x] Cross-tenant UPDATE/DELETE protections
- [x] Dashboard/analytics tenant isolation
- [x] Sales tenant isolation and mandatory authentication
- [x] Documents tenant isolation
- [x] Webhook tenant isolation and application-level SSRF protection
- [x] Data Jobs tenant isolation and dynamic SQL identifier validation
- [x] Payment API authentication/RBAC/tenant binding
- [x] Accounting company/tenant ownership and balanced posting checks
- [x] FastAPI dependency injection security fixes
- [x] Debug/secret-bearing logging regression checks
- [x] Unsafe `eval()` removed from form engine

## 2. CI/CD — GREEN

- [x] Blocking tests fail the workflow on failure
- [x] Blocking Bandit and pip-audit checks fail on failure
- [x] CI summary requires all blocking jobs to succeed
- [x] GitHub Actions are referenced by immutable commit SHA in blocking workflows
- [x] Frontend lint/unit/build gate enabled
- [x] Migration graph/upgrade/alembic-check gate enabled

## 3. Database migrations — GREEN in CI

- [x] Single migration head enforced in CI
- [x] Clean upgrade executed in CI
- [x] `alembic check` executed in CI
- [x] Current model-alignment migration added
- [x] SQLite database artifacts removed from repository
- [ ] Production migration rehearsal on the real deployment topology
- [ ] Production rollback/restore drill

## 4. Frontend/API contract — IMPLEMENTATION GREEN, full contract certification pending

- [x] Canonical frontend selected
- [x] Legacy frontend source retired
- [x] Auth response contract corrected
- [x] `/auth/me` session validation integrated
- [x] Reset-password payload corrected
- [x] Dashboard wired to real analytics API
- [x] Frontend CI lint/test/build gate
- [ ] Generate and commit a reproducible API client from the authoritative OpenAPI schema
- [ ] Full endpoint-by-endpoint OpenAPI ↔ frontend contract certification
- [ ] Commit `frontend/package-lock.json` and use `npm ci` for deterministic builds

## 5. Authorization — GREEN for current tested RBAC boundaries; enterprise policy work remains

- [x] Authentication required by critical routes
- [x] Permission dependency uses the authenticated principal
- [x] Tenant context is authoritative from authentication
- [x] Platform-owner boundary exists
- [x] Authorization regression suite exists
- [ ] Full endpoint/module RBAC matrix certification
- [ ] ABAC/ReBAC/business-rule authorization layer

## 6. Reliability architecture — PARTIAL / code foundation present

- [x] Persistent tenant-scoped event records
- [x] Webhook deliveries are persisted before asynchronous delivery
- [x] Job execution uses tenant-scoped row locking
- [x] Payment/journal critical paths have transaction-aware checks
- [ ] Full transactional outbox for every externally visible side effect
- [ ] Idempotency keys for payments, invoices, orders, journals, webhooks, AI and ERP generation
- [ ] Concurrency/idempotency certification for inventory, sequences, payments and workflows
- [ ] Queue worker authorization/tenant-context/noisy-neighbor controls

## 7. Production infrastructure — HARD GATES; requires deployment evidence

- [x] Production readiness verifier fails closed when evidence is missing
- [x] Production runbook documents required evidence
- [x] Application container runs as non-root
- [x] Docker runtime aligned with the tested Python 3.12 matrix
- [ ] PostgreSQL app role proven non-superuser/non-owner/non-BYPASSRLS
- [ ] Webhook network egress proxy/firewall policy deployed and negatively tested
- [ ] Tenant-isolated production object storage negatively tested
- [ ] Multi-instance application HA/load balancer
- [ ] PostgreSQL HA/failover
- [ ] Redis HA/failover where Redis is used
- [ ] PITR/off-host backups
- [ ] Successful restore drill
- [ ] Measured RTO/RPO
- [ ] Cross-region DR where required by SLA

## 8. Observability — PARTIAL

- [x] Protected Prometheus metrics endpoint
- [x] Structured/request-correlated logging foundations
- [ ] OpenTelemetry distributed tracing deployed
- [ ] SLI/SLO/error-budget definitions and alerts
- [ ] On-call/incident escalation evidence

## 9. Supply chain — PARTIAL

- [x] Dependency vulnerability scan in CI
- [x] Blocking security scan behavior
- [x] Immutable GitHub Action references in blocking workflows
- [ ] Python/frontend/container SBOM artifacts retained per release
- [ ] Container vulnerability scan artifact
- [ ] Image signing and provenance verification
- [ ] Reproducible frontend install using committed lockfile

## 10. Financial correctness — NOT YET CERTIFIED

Required acceptance suite:

- [x] Double-entry balance validation
- [x] Tenant/company ownership validation
- [ ] Trial balance certification
- [ ] P&L certification
- [ ] Balance sheet certification
- [ ] Cash-flow certification
- [ ] Fiscal period controls
- [ ] Period close/reopen
- [ ] Opening balances
- [ ] Dimensions/cost centers
- [ ] Tax accounting
- [ ] Multi-currency revaluation/accounting
- [ ] Retained earnings/year-end close
- [ ] Audit-safe correcting entries

Security CI success is not financial certification.

## 11. ERP Compiler / Dynamic ERP safety — NOT YET CERTIFIED

Required before generated ERP definitions can be deployed:

- [ ] Strict intermediate representation/schema validation
- [ ] Dependency graph validation
- [ ] Authorization-policy validation
- [ ] Migration preview
- [ ] Destructive-change/data-loss detection
- [ ] Generated test validation
- [ ] API/UI contract validation
- [ ] Approval/versioning workflow
- [ ] Deployment rollback

## 12. Compliance / privacy — NOT YET CERTIFIED

- [ ] SOC 2 readiness evidence
- [ ] ISO 27001 control evidence
- [ ] GDPR/privacy controls and DSAR evidence
- [ ] PCI scope assessment where payment functionality requires it
- [ ] Country-specific tax/e-invoicing/localization packs
- [ ] Data residency policy and technical enforcement
- [ ] Retention/deletion/legal-hold policy evidence

## Release rule

The PR may be described as **CI/security GREEN** when all blocking GitHub checks pass. It may be described as **Enterprise Production GREEN** only after every unchecked production/compliance/financial/compiler gate above has real evidence attached to the release.
