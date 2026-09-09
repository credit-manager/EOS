# EOS DBP Staging / Canary Release

1. Build an immutable image from the exact Git SHA.
2. Deploy to staging with production-like PostgreSQL and secret management.
3. Run migrations as a separate controlled step; never create schema on application startup.
4. Run health, auth, tenant-isolation, metadata, records and accounting smoke tests.
5. Run representative load tests and dependency/security scans.
6. Canary 1-5% of traffic with automatic rollback on error-rate, latency or readiness SLO breach.
7. Expand to 25%, 50%, then 100% only after each observation window is healthy.
8. Keep the previous image and database rollback/recovery path available.

## Abort conditions
- Cross-tenant data exposure.
- Migration checksum mismatch.
- Authentication/signing-key failure.
- Accounting imbalance or duplicate posting.
- Sustained elevated 5xx or latency beyond the release SLO.
