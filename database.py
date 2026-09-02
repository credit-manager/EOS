from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import contextvars
from dotenv import load_dotenv

load_dotenv()

# Request-scoped authenticated tenant. Never populate this from a client header.
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
    """Set the transaction-local PostgreSQL RLS tenant context."""
    tid = current_tenant_id.get()
    if tid is not None:
        safe = str(tid).replace("'", "''")
        conn.exec_driver_sql(f"SET LOCAL {RLS_CONTEXT_PARAM} = '{safe}'")


Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(SessionLocal, "before_flush")
def _enforce_orm_tenant_boundary(session, flush_context, instances):
    """Prevent ORM writes from silently using a platform/default tenant.

    Tenant-owned ORM models are expected to expose a ``tenant_id`` attribute.
    Platform/global models should not use this listener because they do not
    carry tenant_id. A tenant request may only write rows for its own tenant.
    """
    tid = current_tenant_id.get()
    for obj in list(session.new) + list(session.dirty):
        if not hasattr(obj, "tenant_id"):
            continue
        obj_tenant = getattr(obj, "tenant_id", None)
        if tid is None:
            if obj_tenant == PLATFORM_TENANT:
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
