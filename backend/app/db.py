import logging
import time
from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

logger = logging.getLogger("2to-eos.db")


class Base(DeclarativeBase):
    pass


settings = get_settings()

engine_kwargs: dict[str, object] = {
    "future": True,
    "pool_pre_ping": True,
}

if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 40
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_timeout"] = 30

engine = create_engine(settings.database_url, **engine_kwargs)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass
class DatabaseHealth:
    is_healthy: bool
    connection_time_ms: float
    pool_status: dict
    error: str | None = None


def check_db_health() -> bool:
    try:
        start_time = time.monotonic()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connection_time = (time.monotonic() - start_time) * 1000

        if connection_time > 1000:
            logger.warning("Slow database connection: %.2fms", connection_time)

        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


def get_db_health() -> DatabaseHealth:
    try:
        start_time = time.monotonic()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connection_time = (time.monotonic() - start_time) * 1000

        pool_status = {}
        if hasattr(engine.pool, "status"):
            pool = engine.pool
            pool_status = {
                "pool_size": getattr(pool, "_pool_size", 0),
                "checked_in": getattr(pool, "_checkedin", 0),
                "checked_out": getattr(pool, "_checkedout", 0),
                "overflow": getattr(pool, "_overflow", 0),
            }

        return DatabaseHealth(
            is_healthy=True,
            connection_time_ms=round(connection_time, 2),
            pool_status=pool_status,
        )
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return DatabaseHealth(
            is_healthy=False,
            connection_time_ms=0,
            pool_status={},
            error=str(exc),
        )


def get_pool_stats() -> dict:
    try:
        pool = engine.pool
        stats = {
            "pool_size": getattr(pool, "_pool_size", 0),
            "checked_in": getattr(pool, "_checkedin", 0),
            "checked_out": getattr(pool, "_checkedout", 0),
            "overflow": getattr(pool, "_overflow", 0),
            "total_connections": getattr(pool, "_total", 0),
        }

        if hasattr(pool, "_timeout"):
            stats["timeout"] = pool._timeout

        if hasattr(pool, "_recycle"):
            stats["recycle"] = pool._recycle

        return stats
    except Exception as exc:
        logger.error("Failed to get pool stats: %s", exc)
        return {}


def log_pool_stats() -> None:
    stats = get_pool_stats()
    if stats:
        logger.info(
            "DB Pool: size=%d, checked_in=%d, checked_out=%d, overflow=%d",
            stats.get("pool_size", 0),
            stats.get("checked_in", 0),
            stats.get("checked_out", 0),
            stats.get("overflow", 0),
        )
