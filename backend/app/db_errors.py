import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError, TimeoutError
from sqlalchemy.orm import Session

from .db import SessionLocal

logger = logging.getLogger("2to-eos.db_errors")


@dataclass
class DatabaseErrorInfo:
    error_type: str
    message: str
    query: str | None = None
    params: dict | None = None
    original_error: Exception | None = None


class DatabaseErrorHandler:
    def __init__(self):
        self._error_counts: dict[str, int] = {}
        self._last_errors: list[DatabaseErrorInfo] = []
        self._max_stored_errors = 100
    
    def handle_error(
        self,
        error: Exception,
        query: str | None = None,
        params: dict | None = None,
    ) -> DatabaseErrorInfo:
        error_type = type(error).__name__
        
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        error_info = DatabaseErrorInfo(
            error_type=error_type,
            message=str(error),
            query=query,
            params=params,
            original_error=error,
        )
        
        self._last_errors.append(error_info)
        if len(self._last_errors) > self._max_stored_errors:
            self._last_errors = self._last_errors[-self._max_stored_errors // 2:]
        
        if isinstance(error, IntegrityError):
            logger.error("Database integrity error: %s", error)
        elif isinstance(error, OperationalError):
            logger.error("Database operational error: %s", error)
        elif isinstance(error, TimeoutError):
            logger.error("Database timeout error: %s", error)
        elif isinstance(error, SQLAlchemyError):
            logger.error("Database SQLAlchemy error: %s", error)
        else:
            logger.error("Database error: %s", error)
        
        return error_info
    
    def get_error_stats(self) -> dict:
        return {
            "error_counts": self._error_counts,
            "total_errors": sum(self._error_counts.values()),
            "last_errors": [
                {
                    "error_type": e.error_type,
                    "message": e.message[:200] if e.message else None,
                }
                for e in self._last_errors[-10:]
            ],
        }
    
    def reset_stats(self) -> None:
        self._error_counts.clear()
        self._last_errors.clear()


error_handler = DatabaseErrorHandler()


@contextmanager
def safe_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        error_handler.handle_error(exc)
        raise
    except OperationalError as exc:
        session.rollback()
        error_handler.handle_error(exc)
        raise
    except TimeoutError as exc:
        session.rollback()
        error_handler.handle_error(exc)
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        error_handler.handle_error(exc)
        raise
    except Exception as exc:
        session.rollback()
        error_handler.handle_error(exc)
        raise
    finally:
        session.close()


def execute_safe_query(
    session: Session,
    query: str,
    params: dict | None = None,
) -> Any:
    try:
        result = session.execute(text(query), params or {})
        return result
    except IntegrityError as exc:
        error_handler.handle_error(exc, query=query, params=params)
        raise
    except OperationalError as exc:
        error_handler.handle_error(exc, query=query, params=params)
        raise
    except TimeoutError as exc:
        error_handler.handle_error(exc, query=query, params=params)
        raise
    except SQLAlchemyError as exc:
        error_handler.handle_error(exc, query=query, params=params)
        raise


def get_db_error_stats() -> dict:
    return error_handler.get_error_stats()


def reset_db_error_stats() -> None:
    error_handler.reset_stats()
