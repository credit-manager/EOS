# EOS DBP v2 — Rebuild Contract

## Objective
Rebuild EOS as a metadata-first ERP platform without deleting the validated legacy baseline. The `main` branch remains the rollback/reference implementation; v2 is migrated by vertical slices.

## Non-negotiable architecture rules
1. **One application composition root**: `eos_v2/app` owns startup, configuration and dependency wiring.
2. **Domain before transport**: business rules do not import FastAPI routers.
3. **Explicit tenant context**: tenant-scoped application services require a tenant context; tenant IDs are never trusted from arbitrary request payloads.
4. **Database is authoritative**: migrations are the only schema evolution mechanism for production.
5. **Metadata is the platform primitive**: entities, fields, relationships, workflows, permissions and UI definitions are data-driven.
6. **Modules are bounded**: Accounting, HR, Inventory, Sales, Projects and Industry Packs integrate through application services/events rather than direct router-to-router calls.
7. **Every vertical slice is testable**: unit, API, tenant-isolation and migration tests are added before promotion.
8. **No compatibility shortcuts in v2**: legacy code may be adapted behind explicit anti-corruption adapters, then removed after migration.

## Target layout
```text
eos_v2/
  app/
    config.py
    app.py
    health.py
    tenant_context.py
  domain/
    metadata/
    identity/
    tenancy/
    workflow/
    permissions/
    accounting/
  application/
    commands/
    queries/
    services/
  infrastructure/
    db/
    events/
    cache/
    files/
  interfaces/
    api/
    workers/
    webhooks/
  modules/
    accounting/
    sales/
    purchasing/
    inventory/
    hr/
    projects/
    industry/
  tests/
```

## Delivery order
1. Runtime/configuration boundary — **started**
2. Persistence boundary + migration contract
3. Tenant/identity/authorization kernel
4. Metadata entity model + metadata API
5. Dynamic record engine
6. Workflow/rules/events
7. Accounting kernel and posting contract
8. Foundation modules
9. Industry packs
10. AI Composer as an application service over metadata
11. Frontend generated from the same metadata contract
12. Observability, performance, security and production deployment
13. Data migration and legacy decommissioning

## Definition of done
A v2 slice is not complete until its code, migration, tests, API contract and operational behavior are all green. No production traffic is switched to v2 until the complete release gate passes.
