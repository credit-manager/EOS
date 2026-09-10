# EOS Dynamic ERP Platform

**EOS — Enterprise Operating System** is a multi-tenant SaaS platform for generating and operating industry-specific ERP systems from metadata, business rules, workflows, and reusable industry packs.

## Production architecture

```text
Business description
        ↓
AI / Builder / Industry Pack
        ↓
Metadata + Validation + Rules + Workflow
        ↓
Tenant-isolated Dynamic API
        ↓
Canonical React frontend
        ↓
Financial / operational / audit services
```

EOS is designed around one reusable core rather than a separate codebase for each customer or industry.

## Production baseline

Production mode is fail-closed. It requires explicit production configuration, database connectivity, controlled CORS/hosts, signed JWT configuration, tenant-aware PostgreSQL RLS, least-privilege database roles, bounded request bodies, rate limiting, audit logging, readiness checks, and structured observability.

Financial data uses decimal database types. Payment transactions start as `pending`; settlement/refund operations require explicit financial authorization. General-ledger posting is protected by database-level accounting invariants.

The official browser application is **`erp-system/frontend`**. The production Docker image builds that source tree and the API serves its generated `dist` artifact at `/ui`.

## Requirements

Development requires Python 3.12+, PostgreSQL 16+, and Node.js 24+.

Production requires Docker Engine / Docker Compose v2+, public DNS, SMTP credentials, live payment credentials when billing is enabled, strong database/runtime/exporter credentials, and an ACME email address for automatic TLS.

## Local development

```bash
git clone https://github.com/credit-manager/EOS.git
cd EOS
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env    # Windows
# cp .env.example .env   # Linux/macOS
```

Set development values in `.env`, then run:

```bash
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The canonical UI is served at `/ui`.

**Do not use `Base.metadata.create_all()` to initialize a production database.** Production schema changes are managed through Alembic migrations only.

## Production deployment

Create a production `.env` from `.env.example` and replace every placeholder. At minimum configure:

```text
ENVIRONMENT=production
EOS_AUTH_MODE=production
EOS_ALGORITHM=HS256
EOS_SECRET_KEY=<strong-random-secret>
DATABASE_URL=<migration-database-url>
POSTGRES_USER=<migration-owner>
POSTGRES_PASSWORD=<strong-secret>
POSTGRES_DB=eos_main
EOS_DB_RUNTIME_USER=eos_runtime
EOS_DB_RUNTIME_PASSWORD=<strong-secret>
EOS_DB_EXPORTER_USER=eos_exporter
EOS_DB_EXPORTER_PASSWORD=<strong-secret>
EOS_FRONTEND_URL=https://app.example.com
EOS_CORS_ORIGINS=["https://app.example.com"]
EOS_ALLOWED_HOSTS=app.example.com
DOMAIN=app.example.com
ACME_EMAIL=ops@example.com
```

Then validate and start:

```bash
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

The production stack uses a dedicated migration role, least-privilege runtime and exporter roles, PostgreSQL RLS, API readiness checks, Nginx, automatic ACME TLS issuance/renewal, Prometheus, Grafana, Alertmanager, Loki, and Promtail.

## Authentication and tenancy

EOS supports production JWT signing/verification with HS256 or RS256. Access tokens are explicitly typed and revalidated against current user state. Tenant context is propagated into PostgreSQL transaction-local RLS settings.

Authentication lookup functions are narrow `SECURITY DEFINER` functions owned by `eos_auth_definer`, a `NOLOGIN`, non-superuser, `BYPASSRLS` role with only the required authentication-table access.

## Dynamic ERP model

Builder and AI-composer capabilities generate metadata-backed entities, forms, lists, validation rules, relationships, workflows, reports, and industry-specific behavior.

The dynamic CRUD layer is tenant-scoped and validates metadata identifiers before SQL interpolation.

## Financial core

EOS includes accounts, journal entries, posting/reversal flows, payment transactions, invoices, subscription/license controls, cash-flow reporting, profit-and-loss reporting, balance-sheet reporting, and customer aging.

Financial reports use posted general-ledger data rather than placeholder totals. Database constraints/triggers protect journal-line sign rules, tenant/account consistency, and immutability of posted entries.

## Industry packs

Reusable industry capabilities cover construction, trading, manufacturing, restaurants, retail, tourism, and services. Industry behavior extends the metadata/rules/workflow core instead of forking the platform.

## Security baseline

- Multi-tenant PostgreSQL Row Level Security with `FORCE ROW LEVEL SECURITY`
- Least-privilege database roles
- Production authentication fail-closed behavior
- Access/refresh token separation
- Explicit financial settlement authorization
- Request-size and Content-Length validation
- HTTPS and security response headers at the edge
- API/auth rate limiting
- Audit logging and request correlation IDs
- SSRF/input/identifier hardening
- Dependency consistency and vulnerability gates
- Reproducible frontend/container build checks

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting.

## Tests and release gates

Run the full suite with:

```bash
pytest -q
```

The commercial release pipeline verifies production configuration, Python/dependency integrity, a single Alembic release head, idempotent migration, tenant RLS, authentication privilege boundaries, production Compose, Nginx/TLS syntax, image vulnerability scans, SBOM generation, canonical frontend build, payment/billing regressions, and the broader CI/security/deployment suite.

A single green check is not a commercial release certification. EOS is considered commercially ready only when the complete verification set is green and the target deployment infrastructure is healthy.

## Development sequence

**CI → Core Hardening → Metadata Platform → Security → Financial Core → Workflow → Industry Packs → AI → Integrations → Globalization → UX → Production Scale**

Reliability and correctness precede scale, breadth, and automation.

## Repository structure

```text
core/                 Platform services and security primitives
routers/              HTTP/API surfaces
models/               Persistent domain models
alembic/versions/     Production database migrations
industry_packs/       Industry-specific modules
erp-system/frontend/  Canonical production frontend
docker/               Production entrypoints and images
nginx/                Edge TLS/routing configuration
monitoring/           Prometheus/Loki/Alertmanager configuration
.github/workflows/    CI, security, release, backup and deployment gates
tests/                Regression and integration tests
```

## License

EOS is proprietary software. See the commercial licensing agreement for production distribution and customer deployments.
