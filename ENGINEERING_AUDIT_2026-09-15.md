# 2TO EOS Engineering Review and Production-Readiness Audit

**Review date / baseline:** 2026-09-15, revalidated against `b34c07d` (and the current branch)
**Scope:** source, migrations, tests, CI, Docker/Compose, deployment documentation, and the shipped frontend. This is a code review of the checked-out repository, not a README review. Status labels below mean **verified in this checkout**, not planned or inferred.

**Arabic version:** [`ENGINEERING_AUDIT_2026-09-15_AR.md`](ENGINEERING_AUDIT_2026-09-15_AR.md).

## A. Executive summary

EOS is a small, modular FastAPI application with a real multi-tenant metadata/record core and several usable backend vertical slices (authentication, auditable dynamic records, basic workflow/rules/events/graph/reporting, financial journals, and a broad construction schema/service layer). It is **not yet an AI-native Business Operating System**. It is primarily a construction ERP/backend prototype with platform components implemented as synchronous, in-process features and a separate, older ERP frontend.

The most important discrepancy is integration: the browser entrypoint renders `frontend/src/App.tsx`, while the newer catalog/entity/metadata UI is an unused named export in `frontend/src/components/App.tsx`. The shipped UI does not expose metadata records, workflows, rules, events, graph, or analytics-report APIs; it bypasses the central API client and ignores `VITE_API_URL`. The repository therefore cannot demonstrate the intended object → relation → workflow → rule → event → analytics → AI story end-to-end.

The backend/platform foundation is safer than a mock: tenant-scoped queries and persisted sessions exist, refresh-token lookup and rotation/reuse protection are implemented, record updates use a version check, financial posting locks accounts, audit/events are persisted, CI installs dependencies and runs dependency audits, production Compose requires secrets, and SQLite migrations reach head. Conversely, the “event bus” dispatches handlers synchronously from a process-global dictionary, rules use a process-global recursion counter, reports load every tenant record into Python, and metadata is not the source of truth for the financial/construction tables. There is no AI, document intelligence, external integration hub, queue/worker, webhook/OAuth/API-key implementation, or user-facing business graph.

**Readiness:** Demo ready: **NOT READY**; Production ready: **NOT READY**; Platform complete: **NOT READY**. The fastest credible outcome is a focused demo built on the existing metadata/records/workflow/rules/graph/reporting APIs—not a rewrite.

### Revalidation corrections (post-`b34c07d`)

The following original findings are explicitly superseded: backend refresh-token hash lookup, rotation, and reuse protection are **implemented**; Nginx **does** proxy `/api/` to `backend:8000`; CI dependency installation/audits and failure gates are present without `continue-on-error`; Compose requires production secrets rather than a placeholder password; and `httpx>=0.28,<1` is declared in the test extra. The remaining authentication finding is strictly a **shipped-frontend integration defect**: root `App.tsx` does not use the existing refresh/logout/configurable-client path.

## B. Repository inventory

| Area | Verified inventory | Assessment |
|---|---|---|
| Root/config | `main.py`, `pyproject.toml`, Alembic config, `.env.example`, two Compose files, API Dockerfile/test Dockerfile, deployment and README docs | Python package has no lockfile; frontend has `package-lock.json`. |
| Backend platform | `auth`, `metadata`, `records`, `workflow`, `rules`, `events`, `graph`, `reporting`, `audit`, `notification`, `lookup` | Routers are included by `backend/app/main.py`; most use synchronous SQLAlchemy sessions. |
| ERP packs | `financial` and `construction` modules, legacy `reports.py`/`reports_router.py`, `export.py`/`export_router.py`, permissions router | Parallel platform/dynamic-record and fixed-table ERP architectures coexist. |
| Frontend | Root `App.tsx`, 20+ components, i18n, simple fetch client | The entrypoint selects the old dashboard/ERP shell. `components/App.tsx`, `CatalogPage`, `EntityPage`, and `MetadataStudio` are dead/unintegrated. |
| Database | 16 migration files from `0001` through `0014`, including two non-sequential Alembic revision IDs | Fresh SQLite upgrade was verified to head; PostgreSQL was not available locally. |
| Tests | 20 backend test modules; no frontend test files despite `node --test` script | Tests are API-focused and do not establish frontend E2E, migration-on-PostgreSQL, security, concurrency, or deployment coverage. |
| CI/CD | one GitHub Actions workflow: Python lint/migrations/tests, dependency audits, frontend lint/format/build, Docker build only on pushes to `main` | No image publishing/deploy, runtime migration, frontend E2E, SBOM, or rollback. |

## C. What is already complete (verified)

1. **Tenant-bound session authentication — implemented, with limits.** Registration creates tenant, user, admin membership, an audit event, a system event, and an auth session in one request transaction. Login issues an access/refresh pair; refresh revokes the old session then creates a new one; `require_principal` validates the persisted session, active user, membership, role, and token hash. Passwords use PBKDF2-HMAC-SHA256 with a per-password salt. This is a meaningful baseline, but lacks reset/activation/lockout/MFA and the delivered frontend does not use refresh or server logout.
2. **Metadata-driven dynamic records — partially complete but functional.** Published metadata controls dynamic field type, required/nullability, defaults, readonly/computed fields, basic validation, record permissions, relation target validation, query filtering, record optimistic-concurrency version, audit, event emission, graph-relation events, and optional workflow creation. Tenant predicates are present in dynamic-record and relation lookups.
3. **Core financial journaling — implemented at a basic ledger level.** Draft creation validates account ownership and debit/credit balance; posting locks referenced accounts, checks balanced lines, marks the entry posted, and audits/events it. This is a real double-entry slice, not merely a UI mock.
4. **Reusable workflow/rule/reporting/graph APIs — partial implementations.** Workflow definitions and instances are tenant-scoped and support configured transitions/approval tasks; rules implement AND conditions with notify/publish-event/audit actions; graph traversal follows dynamic-record relations to depth three; saved reports calculate count/sum/avg/min/max with simple grouping and persist report runs. Audit, notification, and system-event tables are persisted.
5. **Construction backend breadth — implemented but not fully surfaced.** Models/schemas/services cover projects, contracts, BOQ/budgets, claims, change orders, subcontracting, warehouses, procurement, POs, receipts, invoices, payments and financial integration. The delivered frontend exposes only projects/contracts/BOQ/claims/procurements and a basic financial page.
6. **Baseline operational hardening — partial.** Request IDs, security headers, CORS allowlist, request-body limit, timeout, GZip, rate-limit middleware, metrics/health endpoints, query logging, and Docker health checks exist. Docker uses a multistage backend build and Compose requires production secrets.

## D. What is partially complete or misleading

| Capability | Status | Evidence and exact gap |
|---|---|---|
| Metadata Engine V2 | **PARTIAL** | Metadata definitions are versioned and publishable, but records do not store metadata version; publishing does not retire prior published versions or validate compatibility/rollback. Fixed financial/construction schemas bypass it entirely. |
| Policy/RBAC | **PARTIAL** | Metadata provides only `admin`/`member` CRUD lists; a separate static enum/role map exists for ERP pages. There are no custom roles, field/action/approval policies, a unified enforcement point, or DB row-level security. |
| Workflow V2 | **PARTIAL** | State/transition/conditions/role approvals/history/events exist. No assignee identity, delegation, reassignment, timers, escalation, retry, compensation, queue execution, or concurrency/version protection on instances/tasks. |
| Rules engine | **PROTOTYPE** | Only flat AND conditions and three actions are implemented. Rule execution shares the request DB session, has no durable retry/DLQ/idempotency key, and recursion protection is a process-global integer. |
| Event bus | **PROTOTYPE** | `SystemEvent` is a database event log, but dispatch is synchronous in-process callbacks. There is no broker, outbox publisher, consumer offset, retry, DLQ, replay, ordering contract, backpressure, or distributed consumers. |
| Business Graph | **PARTIAL** | A read-only, relation-derived story API exists. Edges are recomputed from record JSON rather than persisted graph state; there is no visual explorer, search, graph permissions beyond metadata read, graph analytics, or scalable traversal/indexing. |
| Reporting/analytics | **PARTIAL** | Saved KPI report and workspace feed APIs exist, but calculations fetch all matching tenant records and filter/group JSON in Python; no dashboard UI for this API, SQL aggregation, scheduled reports, drilldown UI, sharing policy, caching, or retention controls. |
| Financial core | **PARTIAL** | Accounts/journals/balancing/posting exist. Fiscal periods/close, taxes, currencies/FX, AP/AR, receivables allocation, bank reconciliation, statutory reporting, immutable corrections/reversals, and accounting exports are absent or not evidenced. |
| Construction ERP | **PARTIAL** | Broad CRUD/service schema exists, but UI and end-to-end workflows cover only a subset. Document handling, approvals/notifications across the pack, robust audit and operational reporting are not established end-to-end. |
| Internationalization | **PARTIAL** | UI toggles Arabic direction/language, but no locale-aware dates/currencies/numbers/timezones or country tax/fiscal/e-invoicing configuration is implemented. |
| Authentication UX | **BROKEN/partial** | Backend refresh/logout endpoints work; root UI stores only access token under a different key and clears it locally without calling logout. It never invokes its own `refreshToken` helper. |
| Deployment | **PARTIAL** | Compose runs backend/frontend/db/Redis and Nginx proxies `/api/` to the backend. The backend still does not run Alembic before serving, and no production deployment/IaC/runtime topology exists. |

## E. What is missing entirely

* AI tool registry, LLM/provider integration, agent runtime/workforce, prompts, permission-aware tool execution, AI audit/approval, safety budgets, context assembler, and AI observability.
* OCR/uploads, document storage, classification/extraction, invoice/supplier/PO matching, human validation, and document-triggered workflows.
* Integration hub: OAuth, API keys, inbound/outbound webhooks, adapters, delivery attempts, queue, retries/DLQ, logs, and secret management.
* EOS Builder, developer SDK, marketplace, extensibility lifecycle, and tenant-isolated plugin execution.
* Enterprise identity/security controls: password reset/verification, MFA/SSO/SCIM, account lockout, tenant lifecycle/admin tooling, session device management, configurable custom roles/permissions, centralized authorization, and RLS.
* A visual graph explorer, rule/workflow designers, AI copilot UI, and an end-to-end workspace tying platform primitives to ERP business objects.

## F. Security findings

### HIGH — EOS-SEC-01: Access and refresh tokens are readable by any injected script

* **Component/file/function:** shipped frontend, `frontend/src/App.tsx`, `handleLogin`/`handleLogout`.
* **Observed behavior:** access token and user profile are written to `localStorage` (`token`); logout only removes local values and does not call the revocation endpoint. The separately authored refresh-token storage/helper in `frontend/src/api.ts` is unused by the rendered app.
* **Why it matters/exploit:** any same-origin XSS, compromised script, or malicious browser extension can exfiltrate bearer access tokens. A stolen access token remains server-valid until TTL because UI logout does not revoke it.
* **Fix/test:** use a BFF or HttpOnly/Secure/SameSite refresh cookie and in-memory access token; call `/auth/logout`; add browser tests for refresh, expiry and remote rejection after logout.

### HIGH — EOS-SEC-02: No durable event/rule execution boundary for business side effects

* **Component/file/function:** `backend/app/events/service.py`, `publish`/`_dispatch`; `backend/app/rules/engine.py`, `_on_event`/`_evaluate`.
* **Observed behavior:** handlers run synchronously before the outer request commit; handler errors are logged and swallowed. Rule actions modify the same session and only `flush`; process restart or commit failure produces neither a retryable consumer record nor atomic published delivery.
* **Why it matters/exploit:** an event can be committed without the intended rule side effect, or an external side effect added later can occur before transaction rollback. This is an integrity/security issue for approval/financial automation.
* **Fix/test:** transactional outbox + worker + idempotency keys, persisted delivery state and DLQ; integration tests for rollback/restart/duplicate delivery.

### MEDIUM — EOS-SEC-03: Static, inconsistent authorization models

* **Component/file/function:** `backend/app/permissions.py`, `ROLE_PERMISSIONS`; `backend/app/records/router.py`, `_allowed`; `backend/app/metadata/router.py`, `_permissions`.
* **Observed behavior:** fixed ERP permissions and metadata CRUD permissions are separate. Dynamic roles default to member behavior and only understand admin/member; fixed ERP routes have their own checks. There is no unified object/field/action enforcement for exports, reports, graph, events or future AI tools.
* **Why it matters:** a newly added route can bypass the correct authorization model, and enterprise custom/field-level policy cannot be expressed.
* **Fix/test:** one policy service invoked by every service/API; deny by default; resource/field/action tests for every role and tenant.

### INFO — EOS-SEC-04: Local test-environment incompatibility needs a clean CI reproduction

* **Component/file/function:** local review environment; `pyproject.toml` test extra; backend test suite.
* **Observed behavior:** `pyproject.toml` explicitly declares `httpx>=0.28,<1`. In the reviewed local Python 3.14 environment, the resolved Starlette `TestClient` requested `httpx2`, so collection failed. This is **not evidence that `pyproject.toml` omits httpx or that the backend refresh implementation is broken**. The project still has no Python lockfile/constraints file, so exact local dependency resolution is not pinned.
* **Why it matters:** treat the local failure as an environment/reproducibility observation until it is reproduced in a clean supported Python 3.11/3.12 CI environment.
* **Fix/test:** retain the declared `httpx` dependency; run a clean supported-version matrix and record resolved packages. Add constraints/lock only if the team requires byte-for-byte reproducibility.

### LOW — EOS-SEC-05: Browser security model is incomplete

* **Observed behavior:** API security headers exist and `frontend/nginx.conf` proxies `/api/` to `backend:8000`, but the static frontend has no CSP configured and no SRI strategy is present.
* **Fix/test:** CSP appropriate for Vite assets, HTTPS-only gateway, security-header scan against both frontend and API.

### Positive controls verified

JWT signatures, expiry, issuer/type claims and persisted sessions are checked; refresh rotation revokes the old session; passwords have salted PBKDF2 hashes; tenant-bound dynamic-record queries include `tenant_id`; request size/origin/rate controls and production JWT-secret validation are present. These reduce risk but do not resolve the findings above.

## G. Architecture, backend, data and performance findings

* **Architecture:** dependency direction is pragmatic router → service/model rather than a separated domain/application/infrastructure design. Construction service is a 1,897-line transaction-heavy module and model/schema files are 800+/870+ lines, creating a high change-coupling hotspot. The global event-handler registry and global rule depth mean behavior depends on process lifetime and is not horizontally coherent.
* **Transaction lifecycle:** most write routes explicitly commit and roll back on exceptional DB dependencies; records combine record/audit/events/workflow in one transaction. This is a good starting point. However, synchronously dispatched rule callbacks erase failure isolation and do not create a durable outbox boundary.
* **Metadata/dynamic records:** values live in JSON, with only the record's tenant/entity/version columns indexed. JSON field filters use JSON expressions and report code loads rows into memory. At 10 tenants/small datasets this is workable; at 100 tenants/large entity tables, selectively index high-cardinality JSON paths or materialize fields; at 1,000 users/tenants move reporting, search, events and workflow timers to workers; at 10,000 tenants require RLS or shard/partition strategy, quota enforcement, async analytics and a broker.
* **Concurrency:** dynamic records check application version before update but lack SQL compare-and-swap (`WHERE version = :expected`), so two sessions can pass the pre-check and overwrite. Financial posting does lock accounts and validates persisted journal lines, a stronger pattern. Metadata version allocation uses `max(version)+1` without a uniqueness constraint/lock; concurrent creators can produce the same version.
* **Database/migrations:** fresh SQLite `alembic upgrade head` succeeds. This does not prove PostgreSQL, downgrade safety, online migration safety, required indexes, backup/restore or migration-with-real-data behavior. The revision chain interleaves revisions `b27fc...` and `213106...` before numeric revisions, which is legal but makes release ordering harder to reason about. No database-level tenant RLS, composite tenant+foreign-key constraints, or universal unique business identifiers are evidenced.
* **Reliability/observability:** request IDs/logs, metrics, health and Redis fallback exist, but there are no readiness dependency semantics, traces/correlation propagation to workers, metrics storage/alerting, Sentry/error reporting, backup/restore runbook, circuit-breaker integration for real external calls, or load/chaos testing.

## H. Frontend and product/UX findings

* `frontend/src/main.tsx` imports root `App.tsx`; it therefore ships the sidebar/dashboard ERP shell. The metadata catalog/entity/studio implementation in `components/App.tsx` cannot be reached and has no route/import path from the entrypoint.
* Root `App.tsx` directly uses relative `fetch('/api/v1/...')` in every page, while `api.ts` provides configurable `VITE_API_URL`. This is an integration/portability inconsistency—not a Compose routing failure: `frontend/nginx.conf` now proxies `/api/` to `backend:8000`.
* The backend refresh/logout architecture is implemented, but the shipped root UI does not consume it: it stores only an access token in `localStorage`, never invokes `refreshToken`, and clears local state without calling `/auth/logout`. The UI also has no login error feedback (`if (!response.ok) return`), route-level authorization, or deep-linkable browser routes.
* The sidebar exposes construction/finance/reports/users/audit/settings, but no workspace catalog, business graph, workflow worklist/definition editor, rules, events, metadata studio or AI. Construction advanced entities (PO, receipt, invoice, payment, etc.) are backend-only, so the user-requested demo chain cannot be performed in the product.
* Arabic/RTL direction switching is implemented; localization is a small client-side translation map, not locale-aware financial/date/timezone handling. Accessibility and responsive behavior are not validated by tests.

## I. Testing and CI/CD findings

* **Executed:** `alembic upgrade head` to a brand-new SQLite database passed; `ruff check backend main.py` passed; frontend lint, Prettier check and production build passed.
* **Local environment observation:** `pytest -q` could not collect tests in the reviewed Python 3.14 environment because its resolved Starlette test client requested `httpx2`. Since the project explicitly declares `httpx>=0.28,<1`, this is not recorded as a `pyproject.toml` defect or backend test failure; it needs confirmation in the supported CI Python 3.12 matrix.
* Test files exercise auth, audit, metadata, records/workflow, events/rules, graph, reporting, finance, construction and a scripted demo API scenario. They do not provide frontend unit/component/E2E coverage (there are no frontend test files), browser/auth token tests, migration downgrade/production PostgreSQL test evidence locally, API-contract generation, concurrency/race tests, load tests, queue/restart/DLQ tests, SAST/secret scanning, or deployment smoke tests for the complete frontend/API stack.
* CI runs dependency audit, lint, formatting, build and tests on SQLite/PostgreSQL. Docker build/runtime test is intentionally gated to pushes to `main`, not PRs, and starts with an in-memory SQLite database rather than validating production PostgreSQL migrations. There is no deployment, image registry/signing, release/rollback, IaC, or post-deploy verification workflow.

## J. Deployment recommendation

Use the current frontend as a separately built static application only after configuring an explicit `VITE_API_URL` (or Nginx `/api` reverse proxy). Deploy API containers behind an HTTPS ingress/load balancer on a managed container platform; deploy workers separately; use managed PostgreSQL with PITR/backups and managed Redis only for cache/rate-limit—not as the event durability mechanism. Run Alembic as a one-shot, locked release job before serving new API pods. Add a transactional outbox and broker/worker before event-driven financial/workflow side effects. Vercel is suitable for the static frontend, not for the synchronous SQLAlchemy API plus durable workers unless the API/worker/database responsibilities are split.

## K. Product gaps against the stated roadmap

| Roadmap item | Classification | Evidence |
|---|---|---|
| Metadata Engine V2 | PARTIAL | Versioned definitions, validation/defaults/computed fields; no lifecycle compatibility/rollback and fixed packs bypass it. |
| Policy Engine | PROTOTYPE | `policy.py` only evaluates simple conditions; authorization is separate/static. |
| Rules Engine | PROTOTYPE | Flat conditions and three synchronous actions only. |
| Event Bus | PROTOTYPE | Persisted log plus in-process dispatch, not durable async infrastructure. |
| Workflow V2 | PARTIAL | Definitions, transitions, approvals/events; no enterprise task/lifecycle operations. |
| Business Graph | PARTIAL | Relation-derived read API only; no visual/business-intelligence layer. |
| Document Intelligence | MISSING | No OCR/document/upload/model code. |
| Integration Hub | MISSING | No webhook/OAuth/API-key/adapter/delivery code. |
| Reporting/Analytics | PARTIAL | Saved reports/feed exist but are in-memory dynamic-record analytics and not surfaced in shipped UI. |
| AI Tool Registry | MISSING | No AI module/dependency/provider/tool code. |
| AI Workforce | MISSING | No agent runtime or worker orchestration. |
| Globalization | PROTOTYPE | RTL/translation toggle only. |
| EOS Builder | MISSING | Metadata form is unshipped/dead; no builder lifecycle. |
| Developer SDK | MISSING | No SDK/package/API client generation. |
| Marketplace | MISSING | No package/install/catalog implementation. |

## L. Critical defects (verified)

| ID | Severity | Component / file / function | Problem and reproduction | Recommended fix / regression test |
|---|---|---|---|---|
| EOS-BUG-01 | HIGH | Shipped frontend authentication integration — `frontend/src/App.tsx`, `handleLogin`/`handleLogout` | **Backend refresh rotation and logout endpoints are implemented.** The shipped root UI does not use them: it saves only `token`/`user` locally, never invokes `refreshToken`, and never calls `/auth/logout`. Log in, click logout, then send the previously issued bearer token to `/api/v1/auth/me`: it remains valid until TTL. | Unify the shipped app on the existing configurable API client/session architecture; refresh before expiry and call server logout; browser test verifies revoked token returns 401 after UI logout. |
| EOS-BUG-02 | MEDIUM | Event/rules — `events/service.py:publish`, `rules/engine.py:_on_event` | Synchronous handler failure is logged/swallowed and no retry state is persisted. Register a handler that raises, publish/commit, restart: event exists but side effect was never retried. | Outbox/worker/delivery table/DLQ/idempotency; rollback/restart/duplicate tests. |
| EOS-BUG-03 | MEDIUM | Metadata concurrency — `metadata/router.py:create_entity` | Version is `max(version)+1` without a DB uniqueness guard. Two concurrent creates for same tenant/code can calculate the same version. | Unique `(tenant_id, code, version)` plus retry/locking; concurrent creation test. |
| EOS-BUG-04 | MEDIUM | Dynamic records — `records/router.py:update_record` | Version is checked after a read then incremented in memory, not in an atomic compare-and-swap update. Two concurrent PATCHes can both read version N and commit, losing one update. | SQL `UPDATE ... WHERE id/tenant/version` and inspect rowcount; simultaneous PATCH test. |

## M. Demo readiness and fastest path to Demo-Ready EOS

### Current verdict: NOT READY

The backend can support a **limited metadata-first demonstration**, but the app shown to a customer cannot traverse the requested scenario or reveal the platform primitives. There is no opportunity/customer UI, no invoice/payment UI path, no graph/workflow/rules/events UI, no report UI wired to saved analytics, and no AI assistant. The `test_demo_scenario.py` is an API test, not evidence of a browser demo.

### Smallest high-value path (reuse, do not rebuild)

1. Make `components/App.tsx` reachable or merge its catalog/entity/studio capabilities into one routed workspace; remove the competing unused app. Standardize all frontend requests on `api.ts` and configurable API base.
2. Add a focused “Demo Workspace” with **Customer, Opportunity, Contract, Project, Procurement Request, Supplier Invoice, Payment** as metadata entities/records and relation fields. Reuse construction endpoints only where they already supply a real dependency; do not attempt all construction pages.
3. Add pages/panels that call existing graph, workflow, rule, event and analytics APIs: record detail shows relation story, workflow state/approval, rule firing/event history, and report drill-to-source references.
4. Seed a single tenant with realistic deterministic data and roles; create a workflow and high-value invoice rule that emits an event/notification/audit. Show finance posting only after approval.
5. Add a very small, permission-checked AI copilot **after** a server-side tool boundary exists: read-only tools for record summary, graph story, pending approvals and saved report result; log every prompt/tool call and require approval for any future write. Do not wire an LLM directly to arbitrary SQL or write endpoints.
6. Exercise the exact scripted journey: login → workspace → customer/opportunity/contract/project relations → procurement/invoice → approval → payment/journal → analytics → read-only copilot explanation. Add browser E2E tests and a seeded demo reset.

## N. Production readiness blockers

1. **Unify the shipped frontend around the existing platform App/API/session architecture**: make the catalog/entity/studio reachable, use the configurable client, refresh tokens, and server logout; then add UI/API contract tests.
2. Replace in-process event/rule delivery with transactional outbox, worker, idempotency, retry/DLQ and operational monitoring before automating financial/workflow actions.
3. Confirm the already-declared test dependencies in a clean supported Python 3.11/3.12 matrix; optionally lock them if reproducible resolution is a release requirement, then pass SQLite **and PostgreSQL** migrations/tests in CI.
4. Centralize deny-by-default authorization; add custom roles and resource/field/action enforcement, tenant RLS/defense in depth, and IDOR tests across every pack/export/report/graph/event.
5. Finish accounting controls (periods, reversals, audit immutability, currencies/taxes and reconciliation) and construction lifecycle invariants before real money/business data.
6. Add managed deployment topology, migration job, backups/PITR and restore drills, secrets management, TLS/CSP, tracing/metrics/error monitoring, load/failure testing, and incident runbooks.

## O. Prioritized remediation roadmap

| Priority | Task / component | Dependencies / complexity | Files/modules principally affected | Acceptance criteria and tests |
|---|---|---|---|---|
| P0 | Unify the shipped frontend with the existing platform App/API/session architecture | Medium | `main.tsx`, both App files, `api.ts`, Auth screen, catalog/entity/studio | One reachable routed workspace, `VITE_API_URL` client, refresh rotation and server logout used by the rendered app, errors/loading; browser tests prove expiry/logout. |
| P0 | Remove/merge competing frontend apps as part of the unification | Medium | `main.tsx`, both App files, catalog/entity/studio | No dead production app; platform catalog/entity/studio is reachable; build/E2E coverage. |
| P0 | Atomic metadata/record writes | Medium | metadata/record routers, migration | Unique metadata version + CAS record updates; concurrent integration tests. |
| P1 | End-to-end Demo Workspace | Medium | frontend pages, seed fixture, metadata/workflow/rules/report APIs | Exact customer→payment journey visibly shows graph/workflow/rule/event/analytics; Playwright/Cypress smoke test. |
| P1 | Expose advanced construction/finance lifecycle selectively | Medium | construction/financial routers/services and UI | Procurement→invoice→payment path has validations/audit/UI; API/UI contract tests. |
| P1 | Add graph/workflow/rules/event/report panels | Medium | frontend, existing API clients | User can inspect record story, approval, rule execution, event, saved report refs; permission tests. |
| P1 | Read-only AI copilot foundation | High | new server AI/tool/audit modules | Allowlisted permission-aware read tools, server-side provider, prompt/tool audit, no direct DB/write access; adversarial authorization tests. |
| P2 | Durable async platform operations | High | events/rules/workflow, new outbox/worker/broker migrations | Transactional outbox, retries/backoff/DLQ/idempotency/replay metrics; restart/duplicate/rollback tests. |
| P2 | Unified authorization + tenant defense | High | policy/permissions/all routers/services/migrations | Deny by default; custom roles/object/field/action policies, exports/reports/graph/events covered, optional PostgreSQL RLS; tenant/IDOR suite. |
| P2 | Financial production controls | High | financial/construction models/services/migrations | Period close, reversals, currency/tax precision, AP/AR/reconciliation and immutable audit; accounting invariant tests. |
| P2 | Production delivery/operations | High | Docker/Compose/CI/IaC/runbooks | Immutable non-root images, migration release job, registry/signing, TLS gateway, backups/restore drill, alerts/traces and postdeploy checks. |
| P3 | Metadata lifecycle and builder | High | metadata/records/frontend/migrations | Draft/publish/retire/rollback compatibility and visual builder; schema-evolution tests. |
| P3 | Document intelligence/integrations/globalization | High | new bounded services/workers/UI | Secure uploads/OCR review, adapter/webhook delivery controls, locale/timezone/currency/tax/e-invoice capabilities; security/contract/regional tests. |
| P3 | SDK/marketplace/AI workforce | Very high | new product/platform packages | Versioned SDK, isolated extensions, agent jobs/tool policies/observability; sandbox/reliability tests. |

## P. Final scorecard

| Area | Score / 10 | Rationale |
|---|---:|---|
| Architecture | 4 | Good modular start; dual ERP/platform architecture, global sync state and oversized construction service. |
| Backend | 6 | Broad real CRUD/services and transactions; authentication refresh/session protections and CI security gates are implemented, but integration/reliability boundaries are immature. |
| Frontend | 3 | Builds and has basic ERP pages/RTL; key platform UI is unshipped and the shipped app bypasses the existing session/API client architecture. |
| Database | 5 | ORM/migrations/constraints and SQLite fresh upgrade; JSON scaling/RLS/PG evidence/online safety missing. |
| Security | 5 | Refresh rotation, CI dependency audits and production secret requirements improve the baseline; token storage, inconsistent authorization and nondurable side effects still block production. |
| Authentication | 6 | Persisted sessions, refresh lookup/rotation/reuse protection and password hashing are implemented; no MFA/reset/lockout and the shipped frontend fails to consume the lifecycle. |
| Authorization | 3 | Tenant memberships and route checks exist; static/fragmented policy without enterprise coverage. |
| Multi-tenancy | 5 | Dynamic core scopes tenant queries; no RLS/universal defense-in-depth or full-pack proof. |
| Metadata | 5 | Useful definition/validation/relations/versioned publish core; not single source of truth/lifecycle-safe. |
| Dynamic records | 5 | Usable CRUD/validation/audit/events/relations; JSON scale and atomic update gaps. |
| Workflow | 4 | Reusable definitions/transitions/approval skeleton; enterprise task operations missing. |
| Rules | 3 | Basic WHEN/IF/THEN exists; synchronous, small language, no durable operations. |
| Events | 2 | Event log is not a durable asynchronous bus. |
| Business Graph | 3 | Relation story API only, no visual/scalable graph layer. |
| Financial Core | 4 | Balanced journals/posting locks; insufficient full accounting controls. |
| Construction ERP | 4 | Strong schema/service breadth, incomplete user-facing/integrated lifecycle. |
| Analytics | 3 | Saved KPI backend exists but is in-memory and not shipped in platform UI. |
| AI readiness | 0 | No AI implementation. |
| Testing | 3 | Good API test intent, but no frontend/E2E/concurrency/load coverage; the local Python 3.14 collection observation needs confirmation in supported CI rather than being treated as a project packaging defect. |
| CI/CD | 5 | Dependency installation/audits, lint, migration/test and frontend build gates are present without `continue-on-error`; Docker remains main-push-only and release/deploy/rollback are absent. |
| Docker | 5 | Multistage/health basics and Nginx API proxy are present; root runtime, no migration startup, and no production hardening proof remain. |
| Deployment | 3 | Compose requires production secrets and has frontend API proxying; release migrations, IaC, managed topology, rollback and operational controls are absent. |
| Observability | 4 | IDs/logging/metrics/health exist; no tracing/alerts/central telemetry/workers. |
| Documentation | 3 | README/deployment exist; no proven runbooks, architecture truth, backup/DR or contract docs. |
| UX | 3 | Basic page collection, not a coherent operating-system workspace. |
| Demo readiness | 2 | Backend primitives need a focused integrated UI and scenario. |
| Production readiness | 2 | Security/reliability/ops/accounting blockers remain. |
| Platform completeness | 2 | Core prototypes exist; AI/integrations/docs/SDK/marketplace absent. |

## Q. Definition of done

### Demo Ready

- [ ] One deployed, routed workspace using a configured API base and server logout/refresh.
- [ ] Seeded customer → opportunity → contract → project → procurement → invoice → approval → payment journey.
- [ ] Visible dynamic business-object form, relationship graph/story, workflow approval, rule firing/event/audit, KPI report drill-to-source.
- [ ] Deterministic demo tenant reset, role-specific views, loading/error/empty states and browser E2E smoke test.
- [ ] Read-only, permission-aware copilot backed by allowlisted server tools and auditable calls.

### Production Ready

- [ ] All P0/P1/P2 work complete, with a reproducible locked dependency build and clean CI matrix on PostgreSQL.
- [ ] Durable outbox/workers/DLQ/idempotency and failure/restart/concurrency/load test evidence.
- [ ] Central authorization and tenant defense/RLS/IDOR suite across every API/export/report/graph/event.
- [ ] Full accounting controls appropriate to jurisdiction, immutable audit/reversal design, and expert financial review.
- [ ] Secure managed deployment: TLS, secrets, migration gating, backups/PITR plus restore test, monitoring/alerts/tracing, runbooks and incident process.

### EOS Platform V1

- [ ] Production-ready foundations above, lifecycle-safe metadata builder and developer SDK.
- [ ] Visual graph, rule/workflow builders, reporting/analytics at scale and integration/document-intelligence boundaries.
- [ ] AI tool registry/agent execution with permission-aware context, approvals, audit, quotas and observability.
- [ ] Globalization (locale/timezone/currency/tax/fiscal/e-invoicing) and controlled marketplace/extension isolation.
