"""Finalize tenant RLS after the complete canonical schema exists.

Revision ID: 20260909_finalize_tenant_rls
Revises: 20260909_merge_release_heads

The release head runs after schema restoration and normalizes tenant isolation
for every public table that actually has a tenant_id column, including
partitioned tables. The catalog scan prevents tenant tables from silently
escaping the RLS contract because of naming conventions or physical layout.

It also creates a very small set of SECURITY DEFINER lookup functions used
only to discover the tenant for public authentication flows before the caller
can establish the transaction-local RLS context. These functions return only a
tenant identifier and are executable by the application runtime role.
"""

from __future__ import annotations

import os
import re

from alembic import op

revision = "20260909_finalize_tenant_rls"
down_revision = "20260909_merge_release_heads"
branch_labels = None
depends_on = None

RLS_POLICY_PREFIX = "tenant_isolation_"
_SAFE_ROLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _migration_block(down: bool = False) -> str:
    if down:
        return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN pg_attribute AS a ON a.attrelid = c.oid
                                           AND a.attname = 'tenant_id'
                                           AND NOT a.attisdropped
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p')
            LOOP
                v_policy_name := '{RLS_POLICY_PREFIX}' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', v_table_name);
            END LOOP;
        END $$;
        """

    return f"""
        DO $$
        DECLARE
            v_table_name text;
            v_policy_name text;
        BEGIN
            FOR v_table_name IN
                SELECT DISTINCT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN pg_attribute AS a ON a.attrelid = c.oid
                                           AND a.attname = 'tenant_id'
                                           AND NOT a.attisdropped
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p')
            LOOP
                v_policy_name := '{RLS_POLICY_PREFIX}' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format(
                    'CREATE POLICY %I ON public.%I ' ||
                    'USING (tenant_id::text = current_setting(''app.tenant_id'', true)) ' ||
                    'WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
                    v_policy_name, v_table_name
                );
            END LOOP;
        END $$;
        """


def _auth_functions_block() -> str:
    return r"""
        CREATE OR REPLACE FUNCTION public.eos_auth_tenant_by_email(p_email text)
        RETURNS text
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id::text
            FROM public.dbp_users
            WHERE email = lower(p_email)
            LIMIT 1
        $$;

        CREATE OR REPLACE FUNCTION public.eos_auth_tenant_by_verification_hash(p_token_hash text)
        RETURNS text
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id::text
            FROM public.dbp_users
            WHERE verification_token_hash = p_token_hash
              AND email_verified = false
            LIMIT 1
        $$;

        CREATE OR REPLACE FUNCTION public.eos_auth_tenant_by_reset_hash(p_token_hash text)
        RETURNS text
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id::text
            FROM public.dbp_users
            WHERE reset_token_hash = p_token_hash
              AND is_active = true
            LIMIT 1
        $$;

        CREATE OR REPLACE FUNCTION public.eos_auth_tenant_by_refresh_hash(p_token_hash text)
        RETURNS text
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT tenant_id::text
            FROM public.dbp_refresh_tokens
            WHERE token_hash = p_token_hash
            LIMIT 1
        $$;

        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_email(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_verification_hash(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_reset_hash(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_refresh_hash(text) FROM PUBLIC;
    """


def _grant_auth_function_execute() -> None:
    runtime_role = os.getenv("EOS_DB_RUNTIME_USER", "").strip()
    if not runtime_role:
        return
    if not _SAFE_ROLE.fullmatch(runtime_role):
        raise RuntimeError("EOS_DB_RUNTIME_USER must be a simple PostgreSQL role identifier")

    for function_name in (
        "eos_auth_tenant_by_email",
        "eos_auth_tenant_by_verification_hash",
        "eos_auth_tenant_by_reset_hash",
        "eos_auth_tenant_by_refresh_hash",
    ):
        op.execute(
            f'GRANT EXECUTE ON FUNCTION public.{function_name}(text) TO "{runtime_role}"'
        )


def upgrade() -> None:
    op.execute(_migration_block())
    op.execute(_auth_functions_block())
    _grant_auth_function_execute()


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_email(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_verification_hash(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_reset_hash(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_refresh_hash(text);
        """
    )
    op.execute(_migration_block(down=True))
