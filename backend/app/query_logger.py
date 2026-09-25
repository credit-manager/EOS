import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("2to-eos.queries")

SLOW_QUERY_THRESHOLD_MS = 100.0


def setup_query_logging(engine: Engine) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start_time = start_times.pop()
            duration_ms = (time.monotonic() - start_time) * 1000
            
            if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.warning(
                    "Slow query (%.2fms): %s",
                    duration_ms,
                    statement[:200] if len(statement) > 200 else statement,
                )
            elif duration_ms > 10.0:
                logger.debug(
                    "Query (%.2fms): %s",
                    duration_ms,
                    statement[:100] if len(statement) > 100 else statement,
                )


@contextmanager
def log_query_time(operation_name: str) -> Generator[None, None, None]:
    start = time.monotonic()
    try:
        yield
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        if duration_ms > SLOW_QUERY_THRESHOLD_MS:
            logger.warning("Slow operation '%s' took %.2fms", operation_name, duration_ms)
        else:
            logger.debug("Operation '%s' took %.2fms", operation_name, duration_ms)
