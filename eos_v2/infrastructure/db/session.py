from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    url: str
    pool_pre_ping: bool = True
    echo: bool = False

    def validate(self) -> None:
        if not self.url:
            raise ValueError("Database URL is required")
        if not (self.url.startswith("postgresql") or self.url.startswith("sqlite")):
            raise ValueError("Only PostgreSQL and SQLite database URLs are supported")


class Database:
    """Owns SQLAlchemy infrastructure; domain/application layers remain ORM-agnostic."""

    def __init__(self, config: DatabaseConfig) -> None:
        config.validate()
        self.config = config
        self.engine: Engine = create_engine(
            config.url,
            pool_pre_ping=config.pool_pre_ping,
            echo=config.echo,
        )
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check_connection(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
