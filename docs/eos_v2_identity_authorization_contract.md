# EOS DBP v2 — Identity, Tenancy & Authorization Contract

## Security invariants

1. Tenant context is established from authenticated request state, not from business payloads.
2. Every tenant-scoped operation requires an explicit tenant context.
3. Actor membership and resource ownership must match the current tenant context.
4. Missing authentication, inactive actors, tenant mismatch, and unassigned permissions fail closed.
5. Permission checks are centralized in the authorization policy; routers must not implement ad-hoc tenant checks.
6. Domain code remains independent of FastAPI, SQLAlchemy, JWT libraries, and HTTP headers.
7. Identity credentials are infrastructure concerns and must never be stored in domain entities.

## Implemented persistence slice

- `0004_identity_authorization.sql` creates isolated v2 tenant, actor, role and permission-assignment tables.
- Actor subjects are unique within a tenant; role names are unique within a tenant.
- Permissions are explicit values (`read`, `write`, `admin`) and remain deny-by-default.
- JWT access tokens require `sub`, `tenant_id`, `actor_id` and `exp` and are verified with HS256.
- The authenticated tenant claim establishes `TenantContext`; the persisted actor must belong to that tenant and have the same subject.
- The API exposes `/api/v1/auth/me` through a bearer-token dependency that keeps the tenant context active for the request and resets it afterward.
- Persisted role permissions are loaded only for the authenticated actor and current tenant.

## Test contract

SQLite integration tests cover clean model creation, JWT claim requirements, persisted permission loading and cross-tenant actor rejection. PostgreSQL migration execution and upgrade rehearsal remain release-gate responsibilities before staging promotion.

No legacy authentication tables are modified by v2 migrations.
