"""
RATE LIMITING MODULE
====================
DB-backed rate limiter for FastAPI endpoints.

Fixed H1: The in-memory limiter reset on restart and was per-worker,
allowing rate limits to be bypassed across processes/restarts.
Now uses a shared PostgreSQL table so limits are enforced
consistently across workers and after restarts.

Forwarded client addresses are only honored when the immediate peer is
explicitly configured as a trusted proxy, preventing clients from
spoofing X-Forwarded-For to bypass per-IP limits.
"""

import ipaddress
import os
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
    DB-backed fixed-window rate limiter.

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

    @staticmethod
    def _trusted_proxy(peer: str) -> bool:
        """Return whether the immediate peer is an explicitly trusted proxy."""
        configured = os.getenv("EOS_TRUSTED_PROXY_IPS", "")
        if not configured or not peer:
            return False
        try:
            peer_ip = ipaddress.ip_address(peer)
        except ValueError:
            return False
        for value in configured.split(","):
            value = value.strip()
            if not value:
                continue
            try:
                if peer_ip in ipaddress.ip_network(value, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def _default_key_func(self, request: Request) -> str:
        """Use X-Forwarded-For only when the immediate peer is trusted."""
        peer = request.client.host if request.client else ""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded and self._trusted_proxy(peer):
            # The first address is the original client under standard proxy
            # forwarding semantics; malformed values are rejected from keying.
            candidate = forwarded.split(",")[0].strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
        return peer or "unknown"

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

default_limiter = RateLimiter(max_requests=100, window_seconds=60)
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)
read_limiter = RateLimiter(max_requests=200, window_seconds=60)
write_limiter = RateLimiter(max_requests=200, window_seconds=60)
