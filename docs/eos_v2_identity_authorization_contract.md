# EOS DBP v2 — Identity, Tenancy & Authorization Contract

## Security invariants

1. Tenant context is established from authenticated request state, not from business payloads.
2. Every tenant-scoped operation requires an explicit tenant context.
3. Actor membership and resource ownership must match the current tenant context.
4. Missing authentication, inactive actors, tenant mismatch, and unassigned permissions fail closed.
5. Permission checks are centralized in the authorization policy; routers must not implement ad-hoc tenant checks.
6. Domain code remains independent of FastAPI, SQLAlchemy, JWT libraries, and HTTP headers.
7. Identity credentials are infrastructure concerns and must never be stored in domain entities.

## Delivery contract

The next persistence slice will introduce versioned identity/tenant tables and repositories behind these domain contracts. It must include:

- clean-database migration tests;
- upgrade-path migration tests;
- unique tenant and actor identifiers;
- inactive-state handling;
- role/permission assignment with deny-by-default behavior;
- API authentication verification;
- cross-tenant negative tests using real persisted records.

No legacy authentication tables are modified by the v2 migration until an explicit data-migration plan is approved and rehearsed.
