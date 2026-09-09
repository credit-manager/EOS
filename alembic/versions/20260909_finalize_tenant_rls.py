"""Finalize tenant RLS after the complete canonical schema exists.

Revision ID: 20260909_finalize_tenant_rlS
Revises: 20260909_merge_release_heads

The release head normalizes tenant isolation for every public table that has a
 tenant_id column, including partitioned tables. Authentication bootstrap flows
 also need a tenant lookup before the request has an RLS context, so the
 migration creates four narrowly scoped SECURITY DEFINER functions owned by a
 dedicated NOLOGIN BYPASSRLS role. The role has no login capability and only
 SELECT access to the minimum authentication columns required by those
 functions.
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
AUTH_DEFINER_ROLE = "eos_auth_definer"
_SAFE_ROLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _migration_block(down: bool = False) -> str:
    if down:
        return """
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
                v_policy_name := 'tenant_isolation_' || v_table_name;
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'tenant_isolation', v_table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', v_policy_name, v_table_name);
                EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', v_table_name);
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', v_table_name);
            END LOOP;
        END $$;
        """

    return """
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
                v_policy_name := 'tenant_isolation_' || v_table_name;
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


def _auth_role_block(down: bool = False) -> str:
    if down:
        return f"""
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_email(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_verification_hash(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_reset_hash(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.eos_auth_tenant_by_refresh_hash(text) FROM PUBLIC;
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_email(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_verification_hash(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_reset_hash(text);
        DROP FUNCTION IF EXISTS public.eos_auth_tenant_by_refresh_hash(text);
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{AUTH_DEFINER_ROLE}') THEN
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {AUTH_DEFINER_ROLE};
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {AUTH_DEFINER_ROLE};
                REVOKE USAGE ON SCHEMA public FROM {AUTH_DEFINER_ROLE};
                DROP ROLE {AUTH_DEFINER_ROLE};
            END IF;
        END $$;
        """

    return f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{AUTH_DEFINER_ROLE}') THEN
                CREATE ROLE {AUTH_DEFINER_ROLE}
                    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOREPLICATION BYPASSRLS NOINHERIT;
            ELSE
                ALTER ROLE {AUTH_DEFINER_ROLE}
                    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOREPLICATION BYPASSRLS NOINHERIT;
            END IF;
        END $$;

        GRANT USAGE ON SCHEMA public TO {AUTH_DEFINER_ROLE};
        GRANT SELECT (tenant_id, email) ON TABLE public.dbp_users TO {AUTH_DEFINER_ROLE};
        GRANT SELECT (tenant_id, verification_token_hash, email_verified) ON TABLE public.dbp_users TO {AUTH_DEFINER_ROLE};
        GRANT SELECT (tenant_id, reset_token_hash, is_active) ON TABLE public.dbp_users TO {AUTH_DEFINER_ROLE};
        GRANT SELECT (tenant_id, token_hash) ON TABLE public.dbp_refresh_tokens TO {AUTH_DEFINER_ROLE};

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

        ALTER FUNCTION public.eos_auth_tenant_by_email(text) OWNER TO {AUTH_DEFINER_ROLE};
        ALTER FUNCTION public.eos_auth_tenant_by_verification_hash(text) OWNER TO {AUTH_DEFINER_ROLE};
        ALTER FUNCTION public.eos_auth_tenant_by_reset_hash(text) OWNER TO {AUTH_DEFINER_ROLE};
        ALTER FUNCTION public.eos_auth_tenant_by_refresh_hash(text) OWNER TO {AUTH_DEFINER_ROLE};

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
    op.execute(_auth_role_block())
    _grant_auth_function_execute()


def downgrade() -> None:
    op.execute(_auth_role_block(down=True))
    op.execute(_migration_block(down=True))
