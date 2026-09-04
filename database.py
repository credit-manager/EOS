import contextvars
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

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
        cursor.execute(
            """
            SELECT current_user,
                   r.rolsuper,
                   r.rolbypassrls,
                   pg_get_userbyid(d.datdba) AS database_owner
            FROM pg_roles r
            CROSS JOIN pg_database d
            WHERE r.rolname = current_user
              AND d.datname = current_database()
            """
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise RuntimeError("Unable to verify PostgreSQL application role")
        current_user, is_superuser, bypass_rls, database_owner = row
        if is_superuser or bypass_rls or current_user == database_owner:
            raise RuntimeError(
                "Production database role must not be superuser, BYPASSRLS, or database owner"
            )


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
