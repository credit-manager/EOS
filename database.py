from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import contextvars
import re
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# --- RLS tenant scoping ----------------------------------------------------
# Holds the tenant_id for the current request so RLS policies can be applied
# per-session. Set by auth middleware / get_current_user; applied via SET LOCAL
# when a transaction begins on each connection.
current_tenant_id: contextvars.ContextVar = contextvars.ContextVar(
    "current_tenant_id", default=None
)

RLS_CONTEXT_PARAM = "app.tenant_id"


def _get_database_url() -> str:
    """Get DATABASE_URL from the environment; never use hardcoded credentials."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Set it in .env or environment before starting the server."
        )
    return url


DATABASE_URL = _get_database_url()
is_production = os.getenv("EOS_AUTH_MODE", "test").lower() == "production"

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
        cursor = dbapi_connection.cursor()
        cursor.execute("SET statement_timeout = 30000")
        cursor.execute("SET lock_timeout = 10000")
        cursor.close()


@event.listens_for(engine, "begin")
def _set_tenant_on_begin(conn):
    """Inject the authenticated tenant into the transaction for PostgreSQL RLS."""
    tid = current_tenant_id.get()
    if tid is None:
        return

    tid_str = str(tid).strip()
    # '*' is reserved for explicitly approved cross-tenant operations.
    if tid_str != "*" and not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", tid_str):
        raise ValueError(f"Invalid tenant_id format: {tid_str!r}")

    conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = $${tid_str}$$")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a DB session with the current tenant RLS context when authenticated."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_no_rls():
    """Yield a session for explicitly authorized cross-tenant operations."""
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL row_security = off"))
        yield db
    finally:
        db.close()
