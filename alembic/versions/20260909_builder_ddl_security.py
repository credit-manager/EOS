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
BEGIN
    IF p_table_name IS NULL OR p_table_name !~ '^bld_[a-z][a-z0-9_]{0,99}$' THEN
        RAISE EXCEPTION 'Invalid builder table name';
    END IF;

    IF jsonb_typeof(COALESCE(p_columns, '[]'::jsonb)) <> 'array' THEN
        RAISE EXCEPTION 'Builder columns must be a JSON array';
    END IF;

    v_table := p_table_name;
    IF length(v_table) > 63 THEN
        RAISE EXCEPTION 'Builder table name exceeds PostgreSQL identifier limit';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=v_table AND c.relkind IN ('r','p')
    ) THEN
        EXECUTE format(
            'CREATE TABLE public.%I (' ||
            'id VARCHAR(36) PRIMARY KEY,' ||
            'tenant_id VARCHAR(100) NOT NULL,' ||
            'created_at TIMESTAMP DEFAULT NOW()' ||
            ')',
            v_table
        );
    ELSE
        IF NOT EXISTS (
            SELECT 1
              FROM pg_attribute a
              JOIN pg_class c ON c.oid=a.attrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace
             WHERE n.nspname='public'
               AND c.relname=v_table
               AND a.attname='tenant_id'
               AND NOT a.attisdropped
        ) THEN
            RAISE EXCEPTION 'Existing builder table lacks tenant_id';
        END IF;
    END IF;

    FOR col IN SELECT * FROM jsonb_array_elements(COALESCE(p_columns, '[]'::jsonb))
    LOOP
        IF jsonb_typeof(col.value) <> 'object' THEN
            RAISE EXCEPTION 'Invalid builder column definition';
        END IF;
        IF NOT (col.value ? 'code') OR NOT (col.value ? 'sql_type') THEN
            RAISE EXCEPTION 'Builder column requires code and sql_type';
        END IF;
        IF (col.value->>'code') !~ '^[a-z][a-z0-9_]{0,62}$' THEN
            RAISE EXCEPTION 'Invalid builder column code';
        END IF;
        v_type := col.value->>'sql_type';
        IF v_type NOT IN ('VARCHAR(255)','TEXT','INTEGER','DOUBLE PRECISION','BOOLEAN','DATE','TIMESTAMP','VARCHAR(50)','JSONB') THEN
            RAISE EXCEPTION 'Unsupported builder SQL type';
        END IF;
        v_sql := format(
            'ALTER TABLE public.%I ADD COLUMN IF NOT EXISTS %I %s',
            v_table,
            col.value->>'code',
            v_type
        );
        EXECUTE v_sql;
        IF COALESCE((col.value->>'not_null')::boolean, false) THEN
            EXECUTE format(
                'ALTER TABLE public.%I ALTER COLUMN %I SET NOT NULL',
                v_table,
                col.value->>'code'
            );
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
