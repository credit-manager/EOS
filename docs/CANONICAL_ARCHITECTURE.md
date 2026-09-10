# EOS / 2TO Canonical Architecture

## Status

The repository is **one deployable project** with **one application entrypoint**: `main.py`.

`eos_v2/` is not a second application. Its domain, application, infrastructure and API components are internal modules being integrated into the root runtime. No standalone `eos_v2` ASGI application or entrypoint remains.

The legacy implementation (`core/`, `routers/`) is retained only where it still provides production capabilities that have not yet been replaced by the integrated architecture. It is frozen for new feature development except for required security/reliability fixes.

## Current integration

The root FastAPI application includes the integrated v2 metadata, records, accounting, foundation, industry, AI and vertical-slice API routers. They run in the same process and use the canonical deployment configuration and PostgreSQL connection.

The React application is sourced only from `frontend/` and is served from its build artifact under `frontend/dist`.

## Hybrid domain boundary

2TO uses a **Hybrid Metadata Architecture**. Metadata is the default modeling mechanism for flexible business entities; explicit domain models remain authoritative for state with financial or other hard invariants.

### Explicit domain core

An entity or operation belongs to the explicit domain core when it directly creates, changes, validates or settles a state with a non-negotiable invariant, especially:

- general ledger accounts, journal entries and journal lines;
- payment posting and financial settlement;
- inventory balances and stock movements;
- fiscal-period and other ledger controls;
- any operation whose correctness depends on double-entry, balance, ownership or settlement invariants that must be enforced independently of tenant-defined metadata.

These capabilities must keep explicit contracts, explicit persistence and database-enforced invariants. They must not be replaced by arbitrary JSON metadata.

### Metadata-driven domain

An entity is metadata-driven by default when it is a flexible business object that does not itself own a hard financial or balance invariant. Typical examples include:

- customers and suppliers;
- projects and business initiatives;
- subcontractors and evaluations;
- tenant-defined custom entities;
- operational records whose financial effect is represented through an explicit domain operation rather than through the record's arbitrary fields.

Metadata may describe workflow, validation, UI behavior, permissions, relationships and reporting dimensions for these entities.

### Boundary rule for ambiguous entities

A business document may be metadata-driven while its financial effect remains explicit. For example, an invoice-like document may be represented as a tenant-configurable record, but posting receivables, revenue, tax, inventory or payment settlement must enter the explicit financial domain through a defined command/contract.

The classification therefore follows **state ownership**, not the business object's name:

> If it directly owns financial state, ledger state or inventory balance, use an explicit domain contract. Otherwise, metadata is the default.

## Strangler migration rule

`main.py` remains the production composition root while `eos_v2/` reaches capability parity. New canonical platform primitives are built inside `eos_v2/`; legacy `core/` and `routers/` are not the destination for new platform architecture.

Legacy capabilities are migrated **capability-by-capability**. A legacy module is deleted only after its replacement has verified implementation and API/persistence parity, security coverage, frontend compatibility where applicable, CI coverage and no remaining production references.

No mass deletion is permitted based only on filename similarity or a deprecation plan.

## Vertical-slice gate

Before expanding the Metadata Platform broadly, at least one real business slice must prove the complete path:

```text
Metadata definition
    -> PostgreSQL persistence
    -> tenant authorization
    -> dynamic record API
    -> metadata-driven UI
    -> validation / concurrency
    -> workflow transition
    -> audit event
    -> production runtime (`main.py`)
```

The canonical first slice is `subcontractor_evaluation`.

The slice is not considered proven by in-memory tests alone. Its release gate requires a disposable real PostgreSQL database and an executable end-to-end test through the canonical runtime boundaries.

## Deletion gate for remaining legacy code

Legacy modules must be deleted only after every capability they provide has a verified replacement in the integrated architecture and the following gates pass:

1. PostgreSQL migration on a disposable database.
2. Metadata -> records -> business operation E2E through real application/API boundaries.
3. Authentication and tenant isolation tests.
4. Frontend build and functional tests against the canonical API.
5. CI green on the single root runtime.
6. Migration ledger closed with no unresolved capability gaps.
7. No remaining production imports or routes depend on the legacy implementation being removed.

Until all gates pass, deleting `core/` or `routers/` wholesale would risk removing verified functionality. The correct migration operation is capability-by-capability replacement followed by deletion of the obsolete implementation.

## Runtime contract

Run the platform through:

```text
uvicorn main:app
```

There is no second `eos_v2.main` runtime.
