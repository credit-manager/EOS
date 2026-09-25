import logging
import time
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection

logger = logging.getLogger("2to-eos.query_monitor")

_query_count: ContextVar[int] = ContextVar("query_count", default=0)
_query_total_ms: ContextVar[float] = ContextVar("query_total_ms", default=0.0)
_slow_threshold_ms: float = 200.0


@event.listens_for(Connection, "before_cursor_execute")
def _before_cursor_execute(
    conn: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    conn.info.setdefault("query_start", []).append(time.monotonic())


@event.listens_for(Connection, "after_cursor_execute")
def _after_cursor_execute(
    conn: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    starts = conn.info.get("query_start", [])
    if not starts:
        return
    start = starts.pop()
    duration_ms = (time.monotonic() - start) * 1000

    _query_count.set(_query_count.get() + 1)
    _query_total_ms.set(_query_total_ms.get() + duration_ms)

    if duration_ms > _slow_threshold_ms:
        logger.warning("Slow query (%.2fms): %s", duration_ms, statement[:200])


def get_query_stats() -> dict[str, Any]:
    return {
        "query_count": _query_count.get(),
        "total_ms": round(_query_total_ms.get(), 2),
    }


def reset_query_stats() -> None:
    _query_count.set(0)
    _query_total_ms.set(0.0)
