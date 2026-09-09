-- EOS System — Database Initialization
-- This script runs on first PostgreSQL startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create main schema
CREATE SCHEMA IF NOT EXISTS public;

-- Create tenant schema template
CREATE SCHEMA IF NOT EXISTS tenant_template;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE eos_main TO eos;
GRANT ALL PRIVILEGES ON SCHEMA public TO eos;
GRANT ALL PRIVILEGES ON SCHEMA tenant_template TO eos;

-- Create functions for tenant management
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS tenant_%I', tenant_id);
    EXECUTE format('GRANT ALL PRIVILEGES ON SCHEMA tenant_%I TO eos', tenant_id);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION drop_tenant_schema(tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('DROP SCHEMA IF EXISTS tenant_%I CASCADE', tenant_id);
END;
$$ LANGUAGE plpgsql;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'EOS System database initialized successfully';
END $$;
