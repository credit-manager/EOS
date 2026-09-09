#!/bin/bash
# EOS Database Initialization Script
# Runs on first PostgreSQL container startup

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${EOS_DB_RUNTIME_USER:?EOS_DB_RUNTIME_USER is required}"
: "${EOS_DB_RUNTIME_PASSWORD:?EOS_DB_RUNTIME_PASSWORD is required}"

if [ "$POSTGRES_USER" = "$EOS_DB_RUNTIME_USER" ]; then
  echo "EOS_DB_RUNTIME_USER must be different from POSTGRES_USER" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 \
  -v runtime_user="$EOS_DB_RUNTIME_USER" \
  -v runtime_password="$EOS_DB_RUNTIME_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    SET timezone = 'UTC';

    SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'runtime_user', :'runtime_password')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user')
    \gexec

    SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'runtime_user', :'runtime_password')
    WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user')
    \gexec

    SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'runtime_user')
    \gexec
    SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'runtime_user')
    \gexec

    -- The application runtime gets DML on migration-owned tables, but never
    -- blanket function EXECUTE or schema CREATE. Sensitive functions such as
    -- authentication and builder DDL are granted explicitly by migrations.
    SELECT format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I',
      current_user, :'runtime_user'
    )
    \gexec
    SELECT format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
      current_user, :'runtime_user'
    )
    \gexec
    SELECT format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %I',
      current_user, :'runtime_user'
    )
    \gexec

    REVOKE CREATE ON SCHEMA public FROM PUBLIC;
    REVOKE CREATE ON SCHEMA public FROM :"runtime_user";

    \echo 'EOS database initialized successfully with a least-privilege runtime role'
EOSQL
