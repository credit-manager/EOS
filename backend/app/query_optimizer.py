import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import event
from sqlalchemy.orm import Query

logger = logging.getLogger("2to-eos.query_optimizer")

SLOW_QUERY_THRESHOLD_MS = 100.0
VERY_SLOW_QUERY_THRESHOLD_MS = 500.0


@dataclass
class QueryStats:
    query_count: int = 0
    total_time_ms: float = 0.0
    slow_queries: int = 0
    very_slow_queries: int = 0
    last_query_time: float | None = None


class QueryOptimizer:
    def __init__(self):
        self.stats = QueryStats()
        self._query_times: list[float] = []
    
    def record_query(self, duration_ms: float, query: str) -> None:
        self.stats.query_count += 1
        self.stats.total_time_ms += duration_ms
        self.stats.last_query_time = duration_ms
        
        self._query_times.append(duration_ms)
        if len(self._query_times) > 1000:
            self._query_times = self._query_times[-500:]
        
        if duration_ms > VERY_SLOW_QUERY_THRESHOLD_MS:
            self.stats.very_slow_queries += 1
            logger.warning(
                "Very slow query (%.2fms): %s",
                duration_ms,
                query[:200] if len(query) > 200 else query,
            )
        elif duration_ms > SLOW_QUERY_THRESHOLD_MS:
            self.stats.slow_queries += 1
            logger.warning(
                "Slow query (%.2fms): %s",
                duration_ms,
                query[:200] if len(query) > 200 else query,
            )
    
    def get_average_time(self) -> float:
        if not self._query_times:
            return 0.0
        return sum(self._query_times) / len(self._query_times)
    
    def get_stats(self) -> dict:
        return {
            "query_count": self.stats.query_count,
            "total_time_ms": round(self.stats.total_time_ms, 2),
            "average_time_ms": round(self.get_average_time(), 2),
            "slow_queries": self.stats.slow_queries,
            "very_slow_queries": self.stats.very_slow_queries,
            "last_query_time": self.stats.last_query_time,
        }
    
    def reset_stats(self) -> None:
        self.stats = QueryStats()
        self._query_times.clear()


optimizer = QueryOptimizer()


def setup_query_optimization(engine) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.monotonic())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start_time = start_times.pop()
            duration_ms = (time.monotonic() - start_time) * 1000
            
            optimizer.record_query(duration_ms, statement)


def analyze_query(query: Query) -> dict:
    try:
        compilation = query.compile()
        return {
            "sql": str(compilation),
            "params": compilation.params if hasattr(compilation, "params") else {},
        }
    except Exception as exc:
        logger.error("Failed to analyze query: %s", exc)
        return {"error": str(exc)}


@contextmanager
def optimize_query_time(operation_name: str) -> Generator[None, None, None]:
    start = time.monotonic()
    try:
        yield
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        if duration_ms > SLOW_QUERY_THRESHOLD_MS:
            logger.warning("Slow operation '%s' took %.2fms", operation_name, duration_ms)


def get_query_stats() -> dict:
    return optimizer.get_stats()


def reset_query_stats() -> None:
    optimizer.reset_stats()
