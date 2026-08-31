"""
RATE LIMITING MODULE
====================
DB-backed rate limiter for FastAPI endpoints.

Fixed H1: The in-memory limiter reset on restart and was per-worker,
allowing rate limits to be bypassed across processes/restarts.
Now uses a shared PostgreSQL table so limits are enforced
consistently across workers and after restarts.

The limiter lazily connects to the database engine and is fully
compatible with the existing usage pattern:
    limiter = RateLimiter(max_requests=100, window_seconds=60)
    @router.get("/endpoint", dependencies=[Depends(limiter.check)])
"""

import time
from datetime import datetime, timezone
from fastapi import Request, HTTPException, status


def _get_id(text: str) -> int:
    """Deterministic 64-bit hash for rate-limit keying."""
    h = 1469598103934665603
    for ch in text.encode("utf-8"):
        h = ((h ^ ch) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _load_engine():
    """Lazily obtain the shared SQLAlchemy engine."""
    global _ENGINE, _TEXT
    if _ENGINE is None:
        from sqlalchemy import create_engine, text as stext
        import os
        url = os.getenv("DATABASE_URL")
        if not url:
            _ENGINE = None
            _TEXT = stext
            return _ENGINE, _TEXT
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        _TEXT = stext
        with _ENGINE.begin() as conn:
            conn.execute(stext(
                "CREATE TABLE IF NOT EXISTS dbp_rate_limits (\n"
                "    bucket TEXT PRIMARY KEY,\n"
                "    window_start TIMESTAMP NOT NULL,\n"
                "    request_count INTEGER NOT NULL DEFAULT 0\n"
                ")"
            ))
    return _ENGINE, _TEXT


_ENGINE = None
_TEXT = None


class RateLimiter:
    """
    DB-backed sliding window rate limiter.

    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)

        @router.get("/endpoint", dependencies=[Depends(limiter.check)])
        async def endpoint():
            ...
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func=None
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func

    def _default_key_func(self, request: Request) -> str:
        """Default key function: client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _bucket(self, request: Request) -> str:
        key = self.key_func(request)
        return f"rl:{_get_id(key):016x}:{self.window_seconds}"

    def check(self, request: Request) -> None:
        """
        Check if request is allowed atomically against the shared DB.

        Raises HTTPException if rate limit exceeded.
        """
        engine, stext = _load_engine()
        if engine is None:
            return

        bucket = self._bucket(request)
        cur = int(time.time() // self.window_seconds) * self.window_seconds
        cur_start = datetime.fromtimestamp(cur, tz=timezone.utc)
        cur_iso = cur_start.strftime("%Y-%m-%d %H:%M:%S")

        conn = engine.connect()
        try:
            while True:
                conn.execute(stext("BEGIN"))
                row = conn.execute(
                    stext(
                        "SELECT window_start, request_count FROM dbp_rate_limits "
                        "WHERE bucket = :b FOR UPDATE"
                    ),
                    {"b": bucket},
                ).fetchone()

                if row is None:
                    conn.execute(
                        stext(
                            "INSERT INTO dbp_rate_limits "
                            "(bucket, window_start, request_count) "
                            "VALUES (:b, :ws, 1)"
                        ),
                        {"b": bucket, "ws": cur_iso},
                    )
                    conn.execute(stext("COMMIT"))
                    break

                row_start = row[0]
                count = int(row[1])
                row_iso = str(row_start)[:19] if row_start else ""

                if row_iso != cur_iso:
                    # Expired window — reset atomically
                    conn.execute(
                        stext(
                            "UPDATE dbp_rate_limits SET window_start = :ws, "
                            "request_count = 1 WHERE bucket = :b"
                        ),
                        {"b": bucket, "ws": cur_iso},
                    )
                    conn.execute(stext("COMMIT"))
                    break

                if count >= self.max_requests:
                    conn.execute(stext("ROLLBACK"))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Try again later.",
                        headers={
                            "Retry-After": str(self.window_seconds),
                            "X-RateLimit-Limit": str(self.max_requests),
                            "X-RateLimit-Remaining": "0",
                        }
                    )

                conn.execute(
                    stext(
                        "UPDATE dbp_rate_limits SET request_count = request_count + 1 "
                        "WHERE bucket = :b"
                    ),
                    {"b": bucket},
                )
                conn.execute(stext("COMMIT"))
                break
        finally:
            conn.close()


# Pre-configured rate limiters
# Usage: dependencies=[Depends(default_limiter.check)]

# General API: 100 requests per minute
default_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Auth endpoints: 10 requests per minute (stricter)
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Read endpoints: 200 requests per minute (more lenient)
read_limiter = RateLimiter(max_requests=200, window_seconds=60)

# Write endpoints: 200 requests per minute (moderate)
write_limiter = RateLimiter(max_requests=200, window_seconds=60)
