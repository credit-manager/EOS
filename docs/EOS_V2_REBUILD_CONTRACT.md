# EOS / 2TO — v2 Migration Contract

## Objective

Consolidate EOS into one deployable **2TO ERP Platform** without losing production capabilities. `eos_v2/` is the target architecture for new Metadata Platform and Core-domain capabilities. `core/` and `routers/` remain the migration source for capabilities that have not yet reached verified parity.

## Composition root and runtime

- `main.py` is the **only production application composition root** today.
- `eos_v2/` is an integrated internal architecture, not a second ASGI application.
- Production traffic is switched capability-by-capability only after parity and release-gate evidence.

## Hybrid domain boundary

### Metadata-driven by default

Flexible business entities are implemented through `eos_v2` metadata and dynamic records, including custom entities, customers, projects and industry-specific business entities.

### Explicit domain contracts

Financial and inventory invariants remain explicit domain contracts. General ledger, journal posting, inventory balances, payments and financial controls must not become arbitrary JSON workflows. Metadata-driven business documents may invoke these explicit domains through application services.

**Rule:** if an operation changes accounting state, posts a journal, changes a ledger balance, or changes an inventory balance subject to financial invariants, the operation crosses an explicit domain boundary.

## Non-negotiable architecture rules

1. **One composition root:** `main.py` owns runtime composition.
2. **New platform work goes to `eos_v2`:** `core/` changes are limited to required production/security/reliability fixes while capability migration is in progress.
3. **Explicit tenant context:** tenant-scoped operations fail closed when tenant context is absent.
4. **Database is authoritative:** production schema changes are performed through migrations.
5. **Metadata is the platform primitive:** entity, field, relationship, workflow, permission and UI definitions are data-driven.
6. **Bounded domains:** modules integrate through application services and events, not router-to-router coupling.
7. **No deletion without evidence:** a legacy implementation is removed only after duplicate/unreferenced/superseded proof, migration parity, tests and production-traffic review.
8. **No completion without execution evidence:** a feature is only Verified when code, automated tests and real execution evidence support the claim.

## Strangler migration path

1. Keep the root runtime operational.
2. Implement new capabilities in `eos_v2`.
3. Prove each capability through real PostgreSQL/API/runtime tests.
4. Migrate existing capabilities incrementally from `core/` and `routers/`.
5. Cut traffic over only after verified parity.
6. Delete obsolete legacy code only after its capability and references are demonstrably gone.

## Frontend contract

`frontend/` is the canonical React source currently served by `main.py`. The UI should consume the same Metadata contract as the backend; entity-specific screens are temporary bridges and must not replace the generic metadata renderer.

## Definition of Done

A vertical slice is **Verified** only when it has:

- real PostgreSQL persistence;
- real HTTP/API execution;
- tenant isolation and authorization tests;
- workflow and audit evidence;
- canonical runtime integration through `main.py`;
- frontend behavior driven by the same metadata contract where UI is part of the slice.

`pytest` or CI success alone does not qualify as completion.
