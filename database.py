import contextvars
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

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
    """Inject current request tenant into the transaction so RLS policies filter rows."""
    tid = current_tenant_id.get()
    if tid is not None:
        # tenant_id is a sanitized value (UUID / plain identifier) controlled by auth.
        # Defend against any quote/escaping to avoid SQL injection via the GUC value.
        safe = str(tid).replace("'", "''")
        conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = '{safe}'")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Yield a DB session. If a tenant is bound to the current context (via
    authentication), it is applied as app.tenant_id for RLS on this session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
