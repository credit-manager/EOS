"""Enterprise rate limiting for EOS.

Application-level, tenant-aware, atomic fixed-window protection. For global
traffic, deploy Redis/API-gateway rate limiting in front of EOS as well.
"""

import ipaddress
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)
_ENGINE = None
_TEXT = None


def _get_id(text: str) -> int:
    h = 1469598103934665603
    for ch in text.encode("utf-8"):
        h = ((h ^ ch) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _load_engine():
    global _ENGINE, _TEXT
    if _ENGINE is None:
        from sqlalchemy import create_engine, text as stext
        url = os.getenv("DATABASE_URL")
        if not url:
            logger.error("DATABASE_URL is not configured; rate limiting unavailable")
            _TEXT = stext
            return None, _TEXT
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        _TEXT = stext
    return _ENGINE, _TEXT


def _parse_ip(value: str):
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _trusted_networks():
    networks = []
    for raw in os.getenv("EOS_TRUSTED_PROXIES", "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            logger.error("Ignoring invalid EOS_TRUSTED_PROXIES entry")
    return networks


def _get_client_ip(request: Request) -> str:
    raw_client = request.client.host if request.client else "unknown"
    client_ip = _parse_ip(raw_client)
    networks = _trusted_networks()
    if not client_ip or not any(client_ip in network for network in networks):
        return str(client_ip) if client_ip else "unknown"

    candidates = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    for candidate in reversed(candidates):
        parsed = _parse_ip(candidate)
        if parsed and not any(parsed in network for network in networks):
            return str(parsed)
    return str(client_ip)


def _get_tenant_from_request(request: Request) -> Optional[str]:
    user = getattr(request.state, "user", None)
    tenant_id = getattr(user, "tenant_id", None) if user else None
    return str(tenant_id) if tenant_id else None


def _get_user_from_request(request: Request) -> Optional[str]:
    user = getattr(request.state, "user", None)
    user_id = getattr(user, "id", None) if user else None
    return str(user_id) if user_id else None


class RateLimiter:
    """Atomic fixed-window, multi-layer application rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60,
                 key_func=None, limits: Optional[Dict[str, int]] = None,
                 fail_closed: Optional[bool] = None):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.limits = limits or {"ip": 1000, "tenant": 5000, "user": 300, "endpoint": 100}
        self.fail_closed = (fail_closed if fail_closed is not None else
                            os.getenv("EOS_RATE_LIMIT_FAIL_CLOSED", "true").lower() == "true")

    def _default_key_func(self, request: Request) -> str:
        return _get_client_ip(request)

    def _generate_buckets(self, request: Request) -> List[Tuple[str, int]]:
        ip = _get_client_ip(request)
        tenant_id = _get_tenant_from_request(request)
        user_id = _get_user_from_request(request)
        endpoint = request.url.path or "/"
        normalized_ep = "".join(c for c in endpoint if c.isalnum() or c in "/_-:")
        buckets = [
            (f"rl:ip:{_get_id(ip):016x}:{self.window_seconds}", self.limits.get("ip", self.max_requests)),
            (f"rl:ep:{_get_id(normalized_ep):016x}:{self.window_seconds}", self.limits.get("endpoint", self.max_requests)),
        ]
        if tenant_id:
            buckets.extend([
                (f"rl:tenant:{tenant_id}:{self.window_seconds}", self.limits.get("tenant", self.max_requests)),
                (f"rl:ep_tenant:{tenant_id}:{_get_id(normalized_ep):016x}:{self.window_seconds}", self.limits.get("endpoint", self.max_requests)),
            ])
        if user_id:
            buckets.append((f"rl:user:{user_id}:{self.window_seconds}", self.limits.get("user", self.max_requests)))
        return buckets

    def check(self, request: Request) -> None:
        engine, stext = _load_engine()
        if engine is None:
            if self.fail_closed:
                raise HTTPException(status_code=503, detail="Rate limiting service unavailable")
            logger.warning("Rate limiting unavailable; explicit fail-open policy enabled")
            return

        now = time.time()
        window_epoch = int(now // self.window_seconds) * self.window_seconds
        window_start = datetime.fromtimestamp(window_epoch, tz=timezone.utc).replace(tzinfo=None)
        buckets = self._generate_buckets(request)
        placeholders = ", ".join(f":b{i}" for i in range(len(buckets)))
        params = {f"b{i}": bucket for i, (bucket, _limit) in enumerate(buckets)}
        params["ws"] = window_start

        try:
            with engine.begin() as conn:
                for bucket, _limit in buckets:
                    conn.execute(stext(
                        "INSERT INTO dbp_rate_limits (bucket, window_start, request_count) "
                        "VALUES (:b, :ws, 0) ON CONFLICT (bucket) DO NOTHING"),
                        {"b": bucket, "ws": window_start})

                rows = conn.execute(
                    stext(f"SELECT bucket, window_start, request_count FROM dbp_rate_limits "
                          f"WHERE bucket IN ({placeholders}) FOR UPDATE"), params).fetchall()
                state = {row[0]: (row[1], int(row[2])) for row in rows}

                for bucket, limit in buckets:
                    row_start, count = state[bucket]
                    effective_count = 0 if row_start != window_start else count
                    if effective_count >= limit:
                        retry_after = max(1, int(window_epoch + self.window_seconds - time.time()))
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Rate limit exceeded. Try again later.",
                            headers={"Retry-After": str(retry_after),
                                     "X-RateLimit-Limit": str(limit),
                                     "X-RateLimit-Remaining": "0"},
                        )

                for bucket, _limit in buckets:
                    conn.execute(stext(
                        "UPDATE dbp_rate_limits SET window_start = :ws, "
                        "request_count = CASE WHEN window_start <> :ws THEN 1 ELSE request_count + 1 END "
                        "WHERE bucket = :b"), {"ws": window_start, "b": bucket})
        except HTTPException:
            raise
        except Exception:
            logger.exception("Rate limiter database failure")
            if self.fail_closed:
                raise HTTPException(status_code=503, detail="Rate limiting service unavailable")
            logger.warning("Explicit fail-open policy enabled; allowing request")


default_limiter = RateLimiter(max_requests=100, window_seconds=60)
auth_limiter = RateLimiter(max_requests=10, window_seconds=60, limits={"ip": 10, "user": 5, "endpoint": 5})
read_limiter = RateLimiter(max_requests=200, window_seconds=60, limits={"ip": 2000, "tenant": 10000, "user": 500, "endpoint": 200})
write_limiter = RateLimiter(max_requests=100, window_seconds=60, limits={"ip": 1000, "tenant": 5000, "user": 200, "endpoint": 100})
builder_limiter = RateLimiter(max_requests=20, window_seconds=60, limits={"ip": 50, "tenant": 200, "user": 50, "endpoint": 20})
