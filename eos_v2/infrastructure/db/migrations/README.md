# EOS DBP v2 database migration contract

## Rules

- Production schema changes are performed only by versioned migrations.
- The legacy database is read-only from the v2 rebuild until an approved data-migration plan exists.
- No destructive operation (`DROP`, destructive type replacement, or irreversible data rewrite) is permitted without backup, rehearsal, integrity checks, and rollback evidence.
- Every migration must be deterministic, reviewable, and tested against a clean database and a representative upgraded database.
- Data migrations must record source/target row counts and validation queries.
- Application startup must never silently create or alter production schema.

## Current v2 migrations

- `0001_metadata_entities.sql` — tenant-scoped immutable metadata definitions.
- `0002_dynamic_records.sql` — tenant-scoped dynamic records with optimistic row versions.
- `0003_dynamic_record_unique_values.sql` — transactional registry enforcing metadata-defined unique fields and cascading cleanup for deleted records.
- `0004_identity_authorization.sql` — tenants, actors, roles and explicit permission assignments.
- `0005_outbox_events.sql` — durable tenant-scoped event outbox for reliable asynchronous delivery.
- `0006_accounting.sql` — tenant-scoped chart of accounts and double-entry journal storage.

## Record invariants

- Tenant scope is enforced in every repository query and write path.
- Relationship references must resolve to an existing record of the declared target entity in the current tenant.
- Unique field values are scoped by tenant + entity + field and are enforced by a database uniqueness constraint, not only an application pre-check.
- Dynamic values use deterministic tagged JSON serialization for UUID, date, datetime and Decimal domain values.

## Identity invariants

- Access tokens must contain `sub`, `tenant_id`, `actor_id` and `exp`.
- Persisted actor membership is checked against the authenticated tenant and subject.
- Permissions are explicit and deny-by-default.
- Legacy identity/authentication tables are never modified by v2 migrations.

## Event invariants

- Domain events always carry a tenant ID and namespaced event type.
- Outbox writes are transactional with the business transaction; delivery is asynchronous and retryable.
- Event handlers execute under the event's tenant context and cannot inherit another tenant's context.

## Accounting invariants

- Journal lines cannot contain both debit and credit.
- Journal entries require at least two lines and must balance exactly before posting.
- Accounts and journal data are tenant-scoped.
- Account codes are unique within a tenant.
- Posting is an application service operation; no legacy accounting tables are modified.

## Test contract

Repository integration tests use isolated SQLite databases for fast deterministic coverage. PostgreSQL migration execution and upgrade rehearsal remain release-gate responsibilities and must be exercised against clean and representative upgraded PostgreSQL databases before staging promotion.
