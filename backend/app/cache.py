import hashlib
import json
import logging
from collections.abc import Callable
from functools import wraps

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .redis_client import get_redis

logger = logging.getLogger("2to-eos.cache")


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        cache_control: str = "public, max-age=300",
        exclude_paths: list[str] | None = None,
        exclude_methods: list[str] | None = None,
    ):
        super().__init__(app)
        self.cache_control = cache_control
        self.exclude_paths = exclude_paths or [
            "/api/v1/auth/",
            "/api/v1/health",
            "/api/v1/version",
            "/api/v1/ready",
            "/api/v1/metrics",
        ]
        self.exclude_methods = exclude_methods or ["POST", "PUT", "PATCH", "DELETE"]

    def _should_cache(self, request: Request, response: Response) -> bool:
        if request.method in self.exclude_methods:
            return False
        
        path = request.url.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        if response.status_code != 200:
            return False
        
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return False
        
        return True

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if self._should_cache(request, response):
            response.headers["Cache-Control"] = self.cache_control
            response.headers["Vary"] = "Accept, Authorization"
        
        return response


def cache_response(
    ttl: int = 300,
    key_prefix: str = "cache",
    vary_by_user: bool = True,
    exclude_paths: list[str] | None = None,
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Response:
            from fastapi import Request
            from fastapi import Response as StarletteResponse
            
            request = kwargs.get("request") or (args[0] if args else None)
            if not isinstance(request, Request):
                return await func(*args, **kwargs)
            
            path = request.url.path
            if exclude_paths:
                for exclude_path in exclude_paths:
                    if path.startswith(exclude_path):
                        return await func(*args, **kwargs)
            
            cache_key = _generate_cache_key(
                key_prefix=key_prefix,
                request=request,
                vary_by_user=vary_by_user,
            )
            
            redis = None
            try:
                redis = get_redis()
            except Exception:
                pass
            
            if redis:
                try:
                    cached = await redis.get(cache_key)
                    if cached:
                        data = json.loads(cached)
                        return StarletteResponse(
                            content=data["content"],
                            status_code=data["status_code"],
                            headers=data.get("headers", {}),
                            media_type="application/json",
                        )
                except Exception as exc:
                    logger.debug("Cache read error: %s", exc)
            
            response = await func(*args, **kwargs)
            
            if redis and response.status_code == 200:
                try:
                    cache_data = {
                        "content": response.body.decode("utf-8"),
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    }
                    await redis.setex(cache_key, ttl, json.dumps(cache_data))
                except Exception as exc:
                    logger.debug("Cache write error: %s", exc)
            
            return response
        
        wrapper.cache_decorator = True
        return wrapper
    
    return decorator


def _generate_cache_key(
    key_prefix: str,
    request: Request,
    vary_by_user: bool = True,
) -> str:
    parts = [key_prefix, request.method, request.url.path]
    
    if request.query_params:
        sorted_params = sorted(request.query_params.items())
        parts.append(json.dumps(sorted_params, sort_keys=True))
    
    if vary_by_user:
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            parts.append(str(user_id))
    
    key_string = "|".join(parts)
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    return f"{key_prefix}:{key_hash}"


def invalidate_cache(pattern: str) -> None:
    try:
        redis = get_redis()
        keys = []
        for key in redis.scan_iter(match=f"{pattern}*"):
            keys.append(key)
        
        if keys:
            redis.delete(*keys)
            logger.info("Invalidated %d cache keys matching '%s'", len(keys), pattern)
    except Exception as exc:
        logger.warning("Cache invalidation error: %s", exc)
