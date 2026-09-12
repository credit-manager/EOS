import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.app import db as db_module
from backend.app.db import Base


@pytest.fixture(autouse=True)
def _clear_rate_limit_state():
    from backend.app.main import _RATE_LIMIT_STATE
    _RATE_LIMIT_STATE.clear()
    yield
    _RATE_LIMIT_STATE.clear()


@pytest.fixture(autouse=True, scope="session")
def _create_all_tables():
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
