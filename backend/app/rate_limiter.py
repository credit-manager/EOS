import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("2to-eos.ratelimit")

_ACTIVE_INSTANCES: list["RateLimiterBase"] = []


def reset_rate_limiters() -> None:
    """Clear in-memory rate limit buckets across all active limiter instances."""
    for instance in _ACTIVE_INSTANCES:
        instance.buckets.clear()


class RateLimiterBase(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets: dict[str, RateLimitBucket] = defaultdict(RateLimitBucket)
        _ACTIVE_INSTANCES.append(self)


@dataclass
class RateLimitRule:
    max_requests: int
    window_seconds: int
    per: str = "ip"


@dataclass
class RateLimitBucket:
    requests: list = field(default_factory=list)
    blocked_until: float = 0


class AdvancedRateLimitMiddleware(RateLimiterBase):
    def __init__(self, app, rules: dict[str, RateLimitRule] | None = None):
        super().__init__(app)
        self.rules = rules or {
            "default": RateLimitRule(max_requests=100, window_seconds=60),
            "auth": RateLimitRule(max_requests=10, window_seconds=60),
            "write": RateLimitRule(max_requests=30, window_seconds=60),
            "tenant": RateLimitRule(max_requests=200, window_seconds=60),
        }
        self._cleanup_interval = 300
        self._last_cleanup = time.time()

    def _get_rule_key(self, path: str, method: str) -> str:
        if "/auth/" in path:
            return "auth"
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return "write"
        return "default"

    def _cleanup_buckets(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        keys_to_remove = []
        
        for key, bucket in self.buckets.items():
            rule_key = self._get_rule_key(*key.split("|"))
            rule = self.rules.get(rule_key, self.rules["default"])
            cutoff = now - rule.window_seconds
            
            bucket.requests = [t for t in bucket.requests if t > cutoff]
            
            if not bucket.requests and bucket.blocked_until < now:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.buckets[key]

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method
        
        if path in ("/api/v1/health", "/api/v1/version", "/api/v1/ready"):
            return await call_next(request)
        
        rule_key = self._get_rule_key(path, method)
        rule = self.rules.get(rule_key, self.rules["default"])
        
        bucket_key = f"{client}|{path}"
        bucket = self.buckets[bucket_key]
        
        now = time.time()
        
        if bucket.blocked_until > now:
            retry_after = int(bucket.blocked_until - now)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        cutoff = now - rule.window_seconds
        bucket.requests = [t for t in bucket.requests if t > cutoff]
        
        if len(bucket.requests) >= rule.max_requests:
            bucket.blocked_until = now + rule.window_seconds
            retry_after = rule.window_seconds
            
            logger.warning(
                "Rate limit exceeded for %s on %s %s (rule: %s, limit: %d/%ds)",
                client,
                method,
                path,
                rule_key,
                rule.max_requests,
                rule.window_seconds,
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "rule": rule_key,
                    "limit": rule.max_requests,
                    "window": rule.window_seconds,
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + rule.window_seconds)),
                },
            )
        
        bucket.requests.append(now)
        
        self._cleanup_buckets()
        
        response = await call_next(request)
        
        remaining = max(0, rule.max_requests - len(bucket.requests))
        response.headers["X-RateLimit-Limit"] = str(rule.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + rule.window_seconds))
        
        return response


class TenantRateLimitMiddleware(RateLimiterBase):
    def __init__(self, app, tenant_rules: dict[str, RateLimitRule] | None = None):
        super().__init__(app)
        self.tenant_rules = tenant_rules or {
            "free": RateLimitRule(max_requests=50, window_seconds=60),
            "basic": RateLimitRule(max_requests=100, window_seconds=60),
            "pro": RateLimitRule(max_requests=200, window_seconds=60),
            "enterprise": RateLimitRule(max_requests=500, window_seconds=60),
        }
        self._cleanup_interval = 300
        self._last_cleanup = time.time()

    def _cleanup_buckets(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        keys_to_remove = []
        
        for key, bucket in self.buckets.items():
            parts = key.split("|")
            tenant_tier = parts[2] if len(parts) > 2 else "free"
            rule = self.tenant_rules.get(tenant_tier, self.tenant_rules["free"])
            cutoff = now - rule.window_seconds
            
            bucket.requests = [t for t in bucket.requests if t > cutoff]
            
            if not bucket.requests and bucket.blocked_until < now:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.buckets[key]

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method
        
        if path in ("/api/v1/health", "/api/v1/version", "/api/v1/ready"):
            return await call_next(request)
        
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_tier = getattr(request.state, "tenant_tier", "free")
        
        if not tenant_id:
            tenant_id = "anonymous"
            tenant_tier = "free"
        
        rule = self.tenant_rules.get(tenant_tier, self.tenant_rules["free"])
        
        bucket_key = f"{client}|{path}|{tenant_tier}"
        bucket = self.buckets[bucket_key]
        
        now = time.time()
        
        if bucket.blocked_until > now:
            retry_after = int(bucket.blocked_until - now)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Tenant rate limit exceeded",
                    "error_code": "TENANT_RATE_LIMIT_EXCEEDED",
                    "tenant_tier": tenant_tier,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        cutoff = now - rule.window_seconds
        bucket.requests = [t for t in bucket.requests if t > cutoff]
        
        if len(bucket.requests) >= rule.max_requests:
            bucket.blocked_until = now + rule.window_seconds
            retry_after = rule.window_seconds
            
            logger.warning(
                "Tenant rate limit exceeded for tenant %s (tier: %s) on %s %s",
                tenant_id,
                tenant_tier,
                method,
                path,
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Tenant rate limit exceeded",
                    "error_code": "TENANT_RATE_LIMIT_EXCEEDED",
                    "tenant_tier": tenant_tier,
                    "limit": rule.max_requests,
                    "window": rule.window_seconds,
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-TenantRateLimit-Limit": str(rule.max_requests),
                    "X-TenantRateLimit-Remaining": "0",
                    "X-TenantRateLimit-Reset": str(int(now + rule.window_seconds)),
                },
            )
        
        bucket.requests.append(now)
        
        self._cleanup_buckets()
        
        response = await call_next(request)
        
        remaining = max(0, rule.max_requests - len(bucket.requests))
        response.headers["X-TenantRateLimit-Limit"] = str(rule.max_requests)
        response.headers["X-TenantRateLimit-Remaining"] = str(remaining)
        response.headers["X-TenantRateLimit-Reset"] = str(int(now + rule.window_seconds))
        
        return response
