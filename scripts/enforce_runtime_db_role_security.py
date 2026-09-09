"""Enforce production database role security invariants after reconciliation."""

from __future__ import annotations

import os

import psycopg2
from psycopg2 import sql


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def harden_role(cur, role_name: str, allowed_memberships: set[str] | None = None) -> None:
    allowed_memberships = allowed_memberships or set()

    cur.execute(
        sql.SQL(
            "ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOREPLICATION NOBYPASSRLS"
        ).format(sql.Identifier(role_name))
    )

    cur.execute(
        "SELECT parent.rolname "
        "FROM pg_auth_members m "
        "JOIN pg_roles parent ON parent.oid = m.roleid "
        "JOIN pg_roles member ON member.oid = m.member "
        "WHERE member.rolname = %s",
        (role_name,),
    )
    for (parent_name,) in cur.fetchall():
        if parent_name not in allowed_memberships:
            cur.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier(parent_name), sql.Identifier(role_name)
                )
            )

    cur.execute(
        "SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, "
        "rolreplication, rolbypassrls FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    flags = cur.fetchone()
    if flags != (False, False, False, True, False, False):
        raise SystemExit(f"Unsafe PostgreSQL role flags for {role_name!r}: {flags}")


def main() -> None:
    database_url = require("DATABASE_URL")
    runtime_user = require("EOS_DB_RUNTIME_USER")
    exporter_user = require("EOS_DB_EXPORTER_USER")

    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database_name, migration_user = cur.fetchone()
            if migration_user in {runtime_user, exporter_user}:
                raise SystemExit("Runtime roles must not be the migration/database-owner role")

            for role_name in (runtime_user, exporter_user):
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
                if cur.fetchone() is None:
                    raise SystemExit(f"Expected role {role_name!r} does not exist")

            harden_role(cur, runtime_user)
            harden_role(cur, exporter_user, {"pg_monitor"})

            # The exporter is a monitoring principal, not an application principal.
            # Remove any legacy/default function EXECUTE grants that could survive
            # a previous deployment and silently expand its authority later.
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "REVOKE EXECUTE ON FUNCTIONS FROM {}"
                ).format(sql.Identifier(migration_user), sql.Identifier(exporter_user))
            )

            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(runtime_user)
                )
            )
            cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(exporter_user)
                )
            )

    print("Database role security invariants: PASS")


if __name__ == "__main__":
    main()
