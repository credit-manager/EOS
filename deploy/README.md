# EOS DBP v2 production deployment

## Required configuration

Set these values through the deployment secret/configuration system, never in Git:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `EOS_SECRET_KEY` (at least 32 random characters; use a stronger secret in production)
- `EOS_ALLOWED_HOSTS` (comma-separated public hostnames)
- `EOS_CORS_ORIGINS` (comma-separated HTTPS frontend origins)
- Optional AI Composer: `EOS_AI_BASE_URL`, `EOS_AI_API_KEY`, `EOS_AI_MODEL`

## Release sequence

1. Build the v2 image from the exact release commit.
2. Start PostgreSQL and verify its health.
3. Run `python scripts/migrate_v2.py` once against the target database using a controlled deployment job.
4. Run the migration command a second time as an idempotency check in staging.
5. Start the application with the exact same image and configuration.
6. Verify `/health/live` and `/health/ready` through the load balancer.
7. Run tenant-isolation, authentication, metadata, accounting and critical workflow smoke tests.
8. Promote by canary before expanding traffic.

The application container does not automatically mutate the database schema at startup. Migration execution is an explicit deployment operation.
