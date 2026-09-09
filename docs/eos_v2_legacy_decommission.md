# Legacy Migration and Decommission Plan

## Phase 1 — inventory
- Freeze the legacy schema inventory and classify every table by owner, retention, and migration target.
- Map legacy records to the v2 tenant/metadata/module model.

## Phase 2 — rehearsal
- Take a verified backup.
- Execute migration into an isolated v2 database.
- Reconcile row counts, keys, required fields, monetary totals and representative tenant samples.
- Run application and accounting integrity tests.

## Phase 3 — controlled cutover
- Disable legacy writes.
- Perform final incremental migration.
- Validate reconciliation and smoke tests.
- Enable v2 traffic.

## Phase 4 — observation
- Keep legacy read-only for the agreed retention period.
- Monitor discrepancy reports and support incidents.
- Preserve rollback/recovery capability.

## Phase 5 — decommission
- Archive according to legal/contractual retention requirements.
- Revoke legacy credentials and scheduled jobs.
- Remove legacy application traffic only after an explicit release sign-off.
- Do not delete historical data solely to simplify the deployment.
