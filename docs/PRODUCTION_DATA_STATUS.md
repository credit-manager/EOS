# 2TO / EOS — Production Data Status

## Evidence status

**Status: 🟡 Unknown / not verifiable from the repository alone.**

This repository does not contain production database contents, customer records, credentials, or a live production database connection that can be safely inspected from source control. Therefore the project must not claim that production is empty, seeded, or backed up based only on repository state.

## What is proven from source

- `main.py` is the canonical application runtime.
- Production database credentials are expected from environment configuration rather than committed secrets.
- PostgreSQL schema evolution is managed through Alembic migrations.
- No production dataset is committed to the repository.

## Required operational verification before destructive migration

The deployment owner must confirm outside source control:

1. Whether any customer/tenant data is currently served by the production deployment.
2. The production database provider/instance and current database size.
3. Whether an automated backup exists and the latest successful backup timestamp.
4. A restore rehearsal into an isolated database, including application connectivity after restore.
5. The agreed rollback point for the first production capability migration.

Until those facts are verified, legacy production capabilities must be treated as potentially live and protected by the Strangler migration policy.

## Safety rule

No production schema/data deletion, legacy capability removal, destructive migration, or direct production cutover may be justified by the absence of production evidence in Git. Unknown production state is treated as **potentially live**.
