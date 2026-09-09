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

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    -- Set timezone
    SET timezone = 'UTC';

    -- Dedicated application role: never use the migration/database-owner role for API traffic.
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${EOS_DB_RUNTIME_USER}') THEN
            CREATE ROLE "${EOS_DB_RUNTIME_USER}" LOGIN PASSWORD '${EOS_DB_RUNTIME_PASSWORD}';
        ELSE
            ALTER ROLE "${EOS_DB_RUNTIME_USER}" LOGIN PASSWORD '${EOS_DB_RUNTIME_PASSWORD}';
        END IF;
    END
    \$\$;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${EOS_DB_RUNTIME_USER}";
    GRANT USAGE ON SCHEMA public TO "${EOS_DB_RUNTIME_USER}";

    -- Migration-owned tables created later in the same schema automatically receive DML grants.
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${EOS_DB_RUNTIME_USER}";
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
      GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO "${EOS_DB_RUNTIME_USER}";
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
      GRANT EXECUTE ON FUNCTIONS TO "${EOS_DB_RUNTIME_USER}";

    \echo 'EOS database initialized successfully with a dedicated runtime role'
EOSQL
