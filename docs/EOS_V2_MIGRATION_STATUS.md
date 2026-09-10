# EOS v2 Migration Gate

## Decision

`eos_v2/` is the canonical target. Legacy code is frozen and remains temporarily as migration source.

## Verified from `main`

- `eos_v2/main.py` creates the application through `eos_v2.app.create_app()`.
- v2 exposes authentication, metadata, records, accounting, foundation, industry, and AI-composer API boundaries.
- The construction lifecycle test exercises metadata definitions, dynamic records, purchasing, inventory, project cost, lifecycle transitions, and accounting posting.
- The construction lifecycle test currently uses in-memory record/accounting repositories; therefore it is not yet proof of a PostgreSQL/API production path.

## Blocking gates before deletion

- [ ] Real PostgreSQL record repository path proven by integration test.
- [ ] Real HTTP API E2E for metadata -> record -> accounting.
- [ ] Frontend canonical source/build/functional path proven against v2.
- [ ] Authentication and tenant isolation proven on v2 through integration tests.
- [ ] Capability inventory for legacy `core/`, `routers/`, and `eos-system/` has zero unresolved production capabilities.
- [ ] CI runs the canonical v2 backend, database integration, and frontend path.
- [ ] Legacy deletion performed only after all gates are checked.

## Rule

Do not delete legacy directories merely because v2 has a cleaner architecture. Deletion is a controlled migration operation, not a refactor-by-assumption.
