#!/bin/bash
# EOS Database Initialization Script
# Runs on first PostgreSQL container startup

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";

    -- Set timezone
    SET timezone = 'UTC';

    -- Create a read-only role for analytics (optional)
    -- CREATE ROLE eos_readonly;
    -- GRANT CONNECT ON DATABASE eos_production TO eos_readonly;
    -- GRANT USAGE ON SCHEMA public TO eos_readonly;
    -- GRANT SELECT ON ALL TABLES IN SCHEMA public TO eos_readonly;
    -- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO eos_readonly;

    -- Log
    \echo 'EOS database initialized successfully'
EOSQL