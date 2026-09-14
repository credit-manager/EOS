import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.app import db as db_module
from backend.app.db import Base


@pytest.fixture(autouse=True, scope="session")
def _create_all_tables():
    try:
        from backend.app.redis_client import get_redis

        r = get_redis()
        for key in r.scan_iter(match="rate_limit:*"):
            r.delete(key)
        for key in r.scan_iter(match="cache:*"):
            r.delete(key)
    except Exception:
        pass
    if "sqlite" in db_module.engine.url.drivername:
        new_engine = create_engine(
            db_module.engine.url,
            future=True,
            pool_pre_ping=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        db_module.engine.dispose()
        db_module.engine = new_engine
        db_module.SessionLocal.configure(bind=new_engine)
    Base.metadata.create_all(bind=db_module.engine)
    yield
    Base.metadata.drop_all(bind=db_module.engine)


@pytest.fixture(autouse=True)
def _clear_rate_limit_state():
    """Reset rate-limit buckets between tests so no test inherits another
    test's sliding-window state. In-memory buckets (AdvancedRateLimit,
    TenantRateLimit) and Redis-backed auth buckets all accumulate across
    tests; on a fast runner (CI) that tripped 429s on unrelated tests."""
    from backend.app.rate_limiter import reset_rate_limiters

    reset_rate_limiters()
    _clear_redis_prefix("rate_limit:*")
    yield
    reset_rate_limiters()
    _clear_redis_prefix("rate_limit:*")


def _clear_redis_prefix(pattern: str) -> None:
    try:
        from backend.app.redis_client import get_redis

        r = get_redis()
        for key in r.scan_iter(match=pattern):
            r.delete(key)
    except Exception:
        pass
