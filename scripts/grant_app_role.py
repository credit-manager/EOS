"""Grant least-privilege DML rights to the dedicated EOS application role.

This is intended for deployment bootstrap, where DATABASE_URL points to the
schema owner and EOS_DB_APP_USER is the runtime application role.
"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def main() -> None:
    app_user = os.environ["EOS_DB_APP_USER"]
    if not app_user or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in app_user):
        raise SystemExit("EOS_DB_APP_USER contains unsupported characters")

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, pool_pre_ping=True)
    quoted = '"' + app_user.replace('"', '""') + '"'
    with engine.begin() as conn:
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {quoted}"))
        conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted}"))
        conn.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {quoted}"))
    engine.dispose()


if __name__ == "__main__":
    main()
