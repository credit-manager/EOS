"""Database engine/session setup with request-scoped PostgreSQL tenant isolation."""

from __future__ import annotations

import contextvars

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from core.runtime_config import resolve_auth_mode

load_dotenv()

# Holds the authenticated tenant for the current request. The SQLAlchemy begin
# hook copies it into PostgreSQL as a transaction-local GUC consumed by RLS.
current_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_tenant_id", default=None
)
RLS_CONTEXT_PARAM = "app.tenant_id"


def _get_database_url() -> str:
    """Get DATABASE_URL from the environment without credential fallbacks."""
    from os import getenv

    url = getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required")
    return url


DATABASE_URL = _get_database_url()
is_production = resolve_auth_mode() == "production"

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False,
)


if is_production:

    @event.listens_for(engine, "connect")
    def set_postgres_params(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET statement_timeout = 30000")
            cursor.execute("SET lock_timeout = 10000")
        finally:
            cursor.close()


@event.listens_for(engine, "begin")
def _set_tenant_on_begin(conn):
    """Apply the authenticated tenant id as a transaction-local RLS context."""
    tid = current_tenant_id.get()
    if tid is None:
        return
    safe = str(tid).replace("'", "''")
    conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = '{safe}'")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a DB session and always close it after request processing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
