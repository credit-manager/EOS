"""Ensure the production application role exists and has only runtime privileges.

This runs with the migration/database-owner connection so existing PostgreSQL
volumes are upgraded safely even though init-db.sh only executes on first init.
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


def main() -> None:
    database_url = require("DATABASE_URL")
    runtime_user = require("EOS_DB_RUNTIME_USER")
    runtime_password = require("EOS_DB_RUNTIME_PASSWORD")

    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database_name, migration_user = cur.fetchone()

            if runtime_user == migration_user:
                raise SystemExit(
                    "EOS_DB_RUNTIME_USER must differ from the PostgreSQL migration/database-owner role"
                )

            cur.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s",
                (runtime_user,),
            )
            role_exists = cur.fetchone() is not None

            if role_exists:
                cur.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD %s").format(
                        sql.Identifier(runtime_user)
                    ),
                    (runtime_password,),
                )
            else:
                cur.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(
                        sql.Identifier(runtime_user)
                    ),
                    (runtime_password,),
                )

            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(runtime_user)
                )
            )
            cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(runtime_user)
                )
            )
            cur.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE "
                    "ON ALL TABLES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime_user))
            )
            cur.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT, UPDATE "
                    "ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime_user))
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(
                    sql.Identifier(migration_user), sql.Identifier(runtime_user)
                )
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}"
                ).format(
                    sql.Identifier(migration_user), sql.Identifier(runtime_user)
                )
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT EXECUTE ON FUNCTIONS TO {}"
                ).format(
                    sql.Identifier(migration_user), sql.Identifier(runtime_user)
                )
            )

            cur.execute(
                "SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin FROM pg_roles WHERE rolname = %s",
                (runtime_user,),
            )
            role_flags = cur.fetchone()
            if role_flags != (False, False, False, True):
                raise SystemExit(
                    f"Runtime role {runtime_user!r} has unsafe flags: "
                    f"superuser={role_flags[0]}, createrole={role_flags[1]}, "
                    f"createdb={role_flags[2]}, canlogin={role_flags[3]}"
                )

    print(f"Runtime database role ready: {runtime_user}")


if __name__ == "__main__":
    main()
