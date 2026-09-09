"""Ensure production database roles follow least-privilege boundaries.

Runs with the migration/database-owner connection so an existing PostgreSQL
volume is reconciled safely on every deployment. The application runtime role
gets CRUD access; the monitoring exporter role gets PostgreSQL monitoring
privileges only. Runtime DDL is intentionally unavailable except through
narrowly scoped SECURITY DEFINER functions created by migrations.
"""
from __future__ import annotations

import os

import psycopg2
from psycopg2 import sql


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def ensure_login_role(cur, role_name: str, password: str, migration_user: str, database_name: str) -> None:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
    role_exists = cur.fetchone() is not None

    if role_exists:
        cur.execute(
            sql.SQL("ALTER ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role_name)),
            (password,),
        )
    else:
        cur.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role_name)),
            (password,),
        )

    cur.execute(
        "SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolbypassrls FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    role_flags = cur.fetchone()
    if role_flags != (False, False, False, True, False):
        raise SystemExit(
            f"Role {role_name!r} has unsafe flags: "
            f"superuser={role_flags[0]}, createrole={role_flags[1]}, createdb={role_flags[2]}, "
            f"canlogin={role_flags[3]}, bypassrls={role_flags[4]}"
        )

    cur.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(database_name), sql.Identifier(role_name)
        )
    )
    cur.execute(
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
    )


def revoke_function_execute(cur, role_name: str) -> None:
    cur.execute(
        sql.SQL("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {}")
        .format(sql.Identifier(role_name))
    )


def revoke_default_function_execute(cur, migration_user: str, role_name: str | None = None) -> None:
    if role_name is None:
        statement = sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
            "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC"
        ).format(sql.Identifier(migration_user))
    else:
        statement = sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
            "REVOKE EXECUTE ON FUNCTIONS FROM {}"
        ).format(sql.Identifier(migration_user), sql.Identifier(role_name))
    cur.execute(statement)


def main() -> None:
    database_url = require("DATABASE_URL")
    runtime_user = require("EOS_DB_RUNTIME_USER")
    runtime_password = require("EOS_DB_RUNTIME_PASSWORD")
    exporter_user = require("EOS_DB_EXPORTER_USER")
    exporter_password = require("EOS_DB_EXPORTER_PASSWORD")

    if runtime_user == exporter_user:
        raise SystemExit("EOS_DB_RUNTIME_USER and EOS_DB_EXPORTER_USER must differ")

    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database_name, migration_user = cur.fetchone()

            if runtime_user == migration_user or exporter_user == migration_user:
                raise SystemExit(
                    "Application and exporter roles must differ from the PostgreSQL migration/database-owner role"
                )

            # Never depend on PostgreSQL's default public-schema ACLs: make the
            # DDL boundary explicit for every environment, old or new.
            cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

            ensure_login_role(cur, runtime_user, runtime_password, migration_user, database_name)
            ensure_login_role(cur, exporter_user, exporter_password, migration_user, database_name)

            cur.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime_user))
            )
            cur.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime_user))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(sql.Identifier(migration_user), sql.Identifier(runtime_user))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}"
                ).format(sql.Identifier(migration_user), sql.Identifier(runtime_user))
            )

            # PostgreSQL grants EXECUTE on newly created functions to PUBLIC by
            # default. Close that ambient authority for existing and future
            # functions; narrowly scoped migrations explicitly grant EXECUTE.
            cur.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC")
            revoke_function_execute(cur, runtime_user)
            revoke_function_execute(cur, exporter_user)
            revoke_default_function_execute(cur, migration_user)
            revoke_default_function_execute(cur, migration_user, runtime_user)
            revoke_default_function_execute(cur, migration_user, exporter_user)

            cur.execute(sql.SQL("GRANT pg_monitor TO {}").format(sql.Identifier(exporter_user)))

    print(f"Runtime database role ready: {runtime_user}")
    print(f"Monitoring database role ready: {exporter_user}")


if __name__ == "__main__":
    main()
