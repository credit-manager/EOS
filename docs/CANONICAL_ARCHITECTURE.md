# EOS / 2TO Canonical Architecture

## Status

The repository is **one deployable project** with **one application entrypoint**: `main.py`.

`eos_v2/` is not a second application. Its domain, application, infrastructure and API components are internal modules being integrated into the root runtime. No standalone `eos_v2` ASGI application or entrypoint remains.

The legacy implementation (`core/`, `routers/`) is retained only where it still provides production capabilities that have not yet been replaced by the integrated architecture. It is frozen for new feature development except for required security/reliability fixes.

## Current integration

The root FastAPI application includes the integrated v2 metadata, records, accounting, foundation, industry and AI API routers. They run in the same process and use the same deployment configuration and PostgreSQL connection.

The React application is sourced only from `frontend/` and is served from its build artifact under `frontend/dist`.

## Deletion gate for remaining legacy code

Legacy modules must be deleted only after every capability they provide has a verified replacement in the integrated architecture and the following gates pass:

1. PostgreSQL migration on a disposable database.
2. Metadata -> records -> accounting E2E through real application/API boundaries.
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
