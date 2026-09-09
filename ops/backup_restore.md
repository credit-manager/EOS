# EOS DBP Backup / Restore / DR Runbook

## Targets
- Production database: encrypted PostgreSQL backup storage.
- RPO: 15 minutes maximum for production SaaS.
- RTO: 60 minutes maximum for a standard regional failure.

## Backup
1. Take scheduled encrypted PostgreSQL base backups and WAL/archive continuously.
2. Store copies outside the primary compute environment.
3. Retain daily/weekly/monthly recovery points according to the tenant retention policy.
4. Never store database credentials in the repository.

## Restore rehearsal
1. Provision an isolated PostgreSQL instance.
2. Restore the newest full backup plus required WAL.
3. Verify migration ledger and schema checksums.
4. Run the complete v2 test suite and application smoke tests.
5. Reconcile representative row counts and foreign-key integrity.
6. Record measured RTO and recovery timestamp.

## Disaster recovery
- Declare incident and freeze nonessential deployments.
- Restore into the designated recovery environment.
- Validate health/readiness, authentication, tenant isolation and accounting integrity.
- Route traffic only after smoke tests pass.
- Preserve the failed environment for forensic review.
- Rehearse at least quarterly and after major database architecture changes.

## Rollback rule
No destructive migration is permitted without a tested backup and rollback/recovery procedure.
