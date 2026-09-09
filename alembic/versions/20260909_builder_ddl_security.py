"""Secure the dynamic builder's physical-table DDL.

Revision ID: 20260909_builder_ddl_security
Revises: 20260909_finalize_tenant_rls_dynamic
"""
from __future__ import annotations

import os
import re

from alembic import op

revision = "20260909_builder_ddl_security"
down_revision = "20260909_finalize_tenant_rls_dynamic"
branch_labels = None
depends_on = None

SAFE_ROLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_CREATE_FUNCTION = r"""
CREATE OR REPLACE FUNCTION public.eos_create_builder_table(
    p_table_name text,
    p_columns jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    col record;
    v_type text;
    v_sql text;
    v_table text;
    v_code text;
    v_table_exists boolean;
    v_column_exists boolean;
    v_policy_name text;
    v_tenant text;
    v_column_count integer;
BEGIN
    v_tenant := current_setting('app.tenant_id', true);
    IF v_tenant IS NULL OR btrim(v_tenant) = '' THEN
        RAISE EXCEPTION 'Tenant context is required for builder DDL';
    END IF;

    IF p_table_name IS NULL OR p_table_name !~ '^bld_[a-z][a-z0-9_]{0,99}$' THEN
        RAISE EXCEPTION 'Invalid builder table name';
    END IF;
    IF jsonb_typeof(COALESCE(p_columns, '[]'::jsonb)) <> 'array' THEN
        RAISE EXCEPTION 'Builder columns must be a JSON array';
    END IF;
    v_column_count := jsonb_array_length(COALESCE(p_columns, '[]'::jsonb));
    IF v_column_count > 100 THEN
        RAISE EXCEPTION 'Builder tables are limited to 100 custom columns';
    END IF;

    v_table := p_table_name;
    v_policy_name := 'tenant_isolation_' || v_table;
    IF length(v_table) > 63 THEN
        RAISE EXCEPTION 'Builder table name exceeds PostgreSQL identifier limit';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=v_table AND c.relkind IN ('r','p')
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        EXECUTE format(
            'CREATE TABLE public.%I (' ||
            'id VARCHAR(36) PRIMARY KEY,' ||
            'tenant_id VARCHAR(100) NOT NULL,' ||
            'created_at TIMESTAMP DEFAULT NOW()' ||
            ')', v_table
        );
    ELSE
        IF NOT EXISTS (
            SELECT 1 FROM pg_attribute a
            JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=v_table
              AND a.attname='tenant_id' AND NOT a.attisdropped
        ) THEN
            RAISE EXCEPTION 'Existing builder table lacks tenant_id';
        END IF;
    END IF;

    -- Builder-created tables are always tenant-scoped. Reconcile RLS every
    -- time the function is called so old tables are hardened as well.
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', v_table);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', v_table);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table);
    EXECUTE format(
        'CREATE POLICY %I ON public.%I ' ||
        'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
        'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
        v_policy_name, v_table
    );

    FOR col IN SELECT * FROM jsonb_array_elements(COALESCE(p_columns, '[]'::jsonb))
    LOOP
        IF jsonb_typeof(col.value) <> 'object' OR NOT (col.value ? 'code') OR NOT (col.value ? 'sql_type') THEN
            RAISE EXCEPTION 'Invalid builder column definition';
        END IF;
        v_code := col.value->>'code';
        IF v_code !~ '^[a-z][a-z0-9_]{0,62}$' THEN
            RAISE EXCEPTION 'Invalid builder column code';
        END IF;
        IF v_code IN ('id', 'tenant_id', 'created_at') THEN
            RAISE EXCEPTION 'Reserved builder column code';
        END IF;
        v_type := col.value->>'sql_type';
        IF v_type NOT IN ('VARCHAR(255)','TEXT','INTEGER','DOUBLE PRECISION','BOOLEAN','DATE','TIMESTAMP','VARCHAR(50)','JSONB') THEN
            RAISE EXCEPTION 'Unsupported builder SQL type';
        END IF;

        SELECT EXISTS (
            SELECT 1
              FROM pg_attribute a
              JOIN pg_class c ON c.oid=a.attrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace
             WHERE n.nspname='public' AND c.relname=v_table
               AND a.attname=v_code AND NOT a.attisdropped
        ) INTO v_column_exists;

        IF NOT v_column_exists THEN
            v_sql := format('ALTER TABLE public.%I ADD COLUMN %I %s', v_table, v_code, v_type);
            EXECUTE v_sql;
            IF NOT v_table_exists AND COALESCE((col.value->>'not_null')::boolean, false) THEN
                EXECUTE format('ALTER TABLE public.%I ALTER COLUMN %I SET NOT NULL', v_table, v_code);
            END IF;
        ELSE
            SELECT format_type(a.atttypid, a.atttypmod)
              INTO v_type
              FROM pg_attribute a
              JOIN pg_class c ON c.oid=a.attrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace
             WHERE n.nspname='public' AND c.relname=v_table
               AND a.attname=v_code AND NOT a.attisdropped;
            IF v_type IS NULL THEN
                RAISE EXCEPTION 'Unable to inspect existing builder column';
            END IF;
        END IF;
    END LOOP;
END;
$$;
"""


def upgrade() -> None:
    runtime_role = os.getenv("EOS_DB_RUNTIME_USER", "").strip()
    if runtime_role and not SAFE_ROLE.fullmatch(runtime_role):
        raise RuntimeError("EOS_DB_RUNTIME_USER must be a simple PostgreSQL role identifier")
    op.execute(_CREATE_FUNCTION)
    op.execute("ALTER FUNCTION public.eos_create_builder_table(text,jsonb) OWNER TO CURRENT_USER")
    op.execute("REVOKE ALL ON FUNCTION public.eos_create_builder_table(text,jsonb) FROM PUBLIC")
    if runtime_role:
        op.execute(f'GRANT EXECUTE ON FUNCTION public.eos_create_builder_table(text,jsonb) TO "{runtime_role}"')


def downgrade() -> None:
    op.execute("REVOKE ALL ON FUNCTION public.eos_create_builder_table(text,jsonb) FROM PUBLIC")
    op.execute("DROP FUNCTION IF EXISTS public.eos_create_builder_table(text,jsonb)")
