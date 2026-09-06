# EOS DBP v2 database migration contract

## Rules

- Production schema changes are performed only by versioned migrations.
- The legacy database is read-only from the v2 rebuild until an approved data-migration plan exists.
- No destructive operation (`DROP`, destructive type replacement, or irreversible data rewrite) is permitted without backup, rehearsal, integrity checks, and rollback evidence.
- Every migration must be deterministic, reviewable, and tested against a clean database and a representative upgraded database.
- Data migrations must record source/target row counts and validation queries.
- Application startup must never silently create or alter production schema.

## First persistence slice

The first v2 persistence slice intentionally establishes the infrastructure boundary only. Metadata tables will be introduced in a subsequent vertical slice after the migration contract is tested.
