import contextvars
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

current_tenant_id: contextvars.ContextVar = contextvars.ContextVar(
    "current_tenant_id", default=None
)
RLS_CONTEXT_PARAM = "app.tenant_id"
PLATFORM_TENANT = "platform"


def _get_database_url() -> str:
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
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "40")),
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
    """Set transaction-local tenant context for PostgreSQL RLS."""
    tid = current_tenant_id.get()
    if tid is not None:
        safe = str(tid).replace("'", "''")
        conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = '{safe}'")


Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Session, "before_flush")
def _enforce_orm_tenant_boundary(session, flush_context, instances):
    """Prevent ORM writes from silently crossing or inventing tenants."""
    tid = current_tenant_id.get()
    for obj in list(session.new) + list(session.dirty):
        if not hasattr(obj, "tenant_id"):
            continue
        obj_tenant = getattr(obj, "tenant_id", None)
        if tid is None:
            # A tenant-owned object must never be written without an
            # authenticated tenant context.  Global/system objects may keep
            # tenant_id=NULL and are intentionally allowed here.
            if obj_tenant is not None:
                raise ValueError("Tenant context is required for tenant-owned ORM writes")
            continue
        if obj_tenant != tid:
            raise ValueError("Cross-tenant ORM write denied")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
