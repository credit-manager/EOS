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
- `0007_foundation_modules.sql` — tenant-scoped Sales, Purchasing, Inventory, HR and Projects operational storage.
- `0008_industry_pack_installations.sql` — tenant-scoped industry pack installation registry for idempotent retries and version tracking.
- `0009_ai_composer_proposals.sql` — tenant-scoped AI metadata proposals with draft/approved/rejected lifecycle and decision audit timestamps.

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

## Foundation module invariants

- Sales and Purchasing orders are tenant-scoped and use explicit lifecycle transitions: draft → confirmed/cancelled; confirmed → cancelled.
- Inventory balances are tenant-scoped, unique per item, and cannot become negative.
- Employee numbers are unique within a tenant.
- Project dates must satisfy start ≤ end when an end date exists.
- Foundation APIs derive tenant identity exclusively from the authenticated request context.

## Industry pack invariants

- Pack identity is `(tenant_id, pack_key, pack_version)` and is unique in the database.
- Reinstalling an already installed pack version returns the exact previously installed metadata entity IDs instead of creating duplicate metadata versions.
- Pack installation is tenant-bound and requires administrative authorization at the API boundary.
- A builder cannot publish a pack whose built manifest differs from its declared key/version.

## AI Composer invariants

- AI output is an untrusted proposal, never an authorization decision or direct production mutation.
- Proposal changes are tenant-bound by the authenticated context; provider-supplied tenant IDs are ignored.
- Only an authenticated administrator can approve or reject a draft.
- Approval publishes through the existing immutable metadata versioning service inside the same database transaction.
- The provider contract accepts structured metadata only; arbitrary code, SQL, or executable actions are not accepted.
- AI credentials are runtime configuration and are never persisted with proposals.

## Test contract

Repository integration tests use isolated SQLite databases for fast deterministic coverage. PostgreSQL migration execution and upgrade rehearsal remain release-gate responsibilities and must be exercised against clean and representative upgraded PostgreSQL databases before staging promotion.
