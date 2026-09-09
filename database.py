from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from contextvars import ContextVar
import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


def _get_database_url() -> str:
    """
    Get DATABASE_URL from environment.

    No hardcoded passwords. No fallback to credentials.
    Raises ValueError if not set.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Set it in .env or environment before starting the server."
        )
    return url


DATABASE_URL = _get_database_url()
is_production = os.getenv("EOS_AUTH_MODE", "test").lower() == "production"

# ──────────────────────────────────────────────────────────────
# TENANT ISOLATION — Row-Level Security (RLS)
# ──────────────────────────────────────────────────────────────
# Context variable to hold the current tenant ID for RLS.
# Set by auth middleware after JWT verification.
# PostgreSQL RLS policies use this via SET LOCAL.

RLS_CONTEXT_PARAM = "app.tenant_id"
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False,
)


@event.listens_for(engine, "begin")
def _set_tenant_on_begin(conn):
    """
    Inject current tenant into PostgreSQL session for RLS policies.
    
    This fires when a new transaction begins. SET LOCAL is transaction-scoped,
    so it automatically resets when the transaction ends.
    """
    tid = current_tenant_id.get()
    if tid is not None:
        # Sanitize tenant_id to prevent SQL injection via GUC
        safe = str(tid).replace("'", "''")
        conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = '{safe}'")


if is_production:
    @event.listens_for(engine, "connect")
    def set_postgres_params(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET statement_timeout = 30000")
        cursor.execute("SET lock_timeout = 10000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Database session dependency with proper error handling.
    
    Automatically rolls back on exception.
    Ensures session is always closed.
    Routes that modify data should call db.commit() explicitly.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
