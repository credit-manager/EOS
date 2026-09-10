# EOS Canonical Architecture

## Status

`eos_v2/` is the canonical architecture and the only path for new product development.

The legacy implementation (`core/`, `routers/`, and `eos-system/`) is migration source code only. It is frozen except for security fixes required to keep the current release safe during migration.

## Deletion gate

Legacy code must not be deleted until every production capability has a verified v2 replacement and the following gates pass:

1. PostgreSQL migration on a disposable database.
2. Metadata -> records -> accounting E2E through real application/API boundaries.
3. Authentication and tenant isolation tests.
4. Frontend build and functional tests against the canonical API.
5. CI green on the canonical runtime.
6. Migration ledger closed with no unresolved capability gaps.

Until all gates pass, deleting legacy directories would risk removing functionality that has not yet been ported.

## Runtime

The v2 application entrypoint is `eos_v2/main.py` and creates the application through `eos_v2.app.create_app()`.
