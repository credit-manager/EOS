"""Create and grant the least-privilege EOS runtime database role."""
import os

from sqlalchemy import create_engine, text


def _safe_identifier(value: str) -> str:
    if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in value):
        raise SystemExit("EOS_DB_APP_USER contains unsupported characters")
    return '"' + value.replace('"', '""') + '"'


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> None:
    app_user = os.environ["EOS_DB_APP_USER"]
    app_password = os.environ["EOS_DB_APP_PASSWORD"]
    database_url = os.environ["DATABASE_URL"]
    if not app_password:
        raise SystemExit("EOS_DB_APP_PASSWORD is required")

    engine = create_engine(database_url, pool_pre_ping=True)
    quoted_user = _safe_identifier(app_user)
    password_literal = _sql_literal(app_password)
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": app_user}).scalar()
        if not exists:
            conn.exec_driver_sql(f"CREATE ROLE {quoted_user} LOGIN PASSWORD {password_literal} NOSUPERUSER NOBYPASSRLS")
        else:
            conn.exec_driver_sql(f"ALTER ROLE {quoted_user} NOSUPERUSER NOBYPASSRLS LOGIN PASSWORD {password_literal}")
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {quoted_user}"))
        # Existing tables are granted here; future tables receive the same rights
        # through ALTER DEFAULT PRIVILEGES so migrations remain usable by the app.
        conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted_user}"))
        conn.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {quoted_user}"))
        owner = conn.execute(text("SELECT current_user")).scalar()
        conn.exec_driver_sql(f"ALTER DEFAULT PRIVILEGES FOR ROLE {_safe_identifier(owner)} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted_user}")
        conn.exec_driver_sql(f"ALTER DEFAULT PRIVILEGES FOR ROLE {_safe_identifier(owner)} IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {quoted_user}")
    engine.dispose()


if __name__ == "__main__":
    main()
