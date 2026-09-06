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

## Record invariants

- Tenant scope is enforced in every repository query and write path.
- Relationship references must resolve to an existing record of the declared target entity in the current tenant.
- Unique field values are scoped by tenant + entity + field and are enforced by a database uniqueness constraint, not only an application pre-check.
- Dynamic values use deterministic tagged JSON serialization for UUID, date, datetime and Decimal domain values.

## Test contract

Repository integration tests use an isolated SQLite database for fast deterministic coverage. PostgreSQL migration execution remains a release-gate responsibility and must be exercised against a clean and upgraded PostgreSQL database before staging promotion.
