"""Ensure production database roles follow least-privilege boundaries.

Runs with the migration/database-owner connection so an existing PostgreSQL
volume is reconciled safely on every deployment. The application runtime role
gets CRUD access; the monitoring exporter role gets PostgreSQL monitoring
privileges only.
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
        "SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    role_flags = cur.fetchone()
    if role_flags != (False, False, False, True):
        raise SystemExit(
            f"Role {role_name!r} has unsafe flags: "
            f"superuser={role_flags[0]}, createrole={role_flags[1]}, "
            f"createdb={role_flags[2]}, canlogin={role_flags[3]}"
        )

    cur.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(database_name), sql.Identifier(role_name)
        )
    )
    cur.execute(
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
    )
    cur.execute(
        sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO {}").format(
            sql.Identifier(migration_user), sql.Identifier(role_name)
        )
    )


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

            # pg_monitor grants access to PostgreSQL's monitoring views without
            # granting table DML or ownership privileges to the exporter.
            cur.execute(
                sql.SQL("GRANT pg_monitor TO {}").format(sql.Identifier(exporter_user))
            )

    print(f"Runtime database role ready: {runtime_user}")
    print(f"Monitoring database role ready: {exporter_user}")


if __name__ == "__main__":
    main()
