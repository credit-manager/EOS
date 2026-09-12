import os
import re
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .audit.router import router as audit_router
from .auth.router import router as auth_router
from .config import get_settings
from .construction.router import router as construction_router
from .db import Base, engine
from .financial.router import router as financial_router
from .health import router as health_router
from .lookup.router import router as lookup_router
from .metadata.router import router as metadata_router
from .records.router import router as records_router
from .workflow.router import router as workflow_router

settings = get_settings()
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Never run schema creation during a Vercel serverless cold start.  Serverless
    # instances are ephemeral and production schema changes belong to migrations.
    if settings.app_env != "production" and not _IS_VERCEL:
        Base.metadata.create_all(bind=engine)
    yield


_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RATE_LIMIT_TRACKED_ROUTES = frozenset({"POST:/api/v1/auth/token", "POST:/api/v1/auth/register"})
_RATE_LIMIT_STATE: dict[tuple[str, str], deque[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter for authentication endpoints.

    Defends /auth/token and /auth/register against credential stuffing
    and brute force. Keyed by (client IP, route); standard library only.
    Counts every attempt so that distributed guessing is throttled
    regardless of success or failure.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        route_key = f"{request.method}:{request.url.path}"
        if route_key not in _RATE_LIMIT_TRACKED_ROUTES:
            return await call_next(request)
        limit = get_settings().rate_limit_auth_per_minute
        if limit <= 0:
            return await call_next(request)
        client = request.client.host if request.client is not None else "unknown"
        bucket_key = (client, route_key)
        now = time.monotonic()
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        bucket = _RATE_LIMIT_STATE.get(bucket_key)
        if bucket is None:
            bucket = deque()
            if len(_RATE_LIMIT_STATE) > 20000:
                _RATE_LIMIT_STATE.clear()
            _RATE_LIMIT_STATE[bucket_key] = bucket
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(bucket[0] + _RATE_LIMIT_WINDOW_SECONDS - now))
            return JSONResponse(
                status_code=429,
                content={"detail": "too many authentication attempts, try again later"},
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        return await call_next(request)


class _BodyTooLargeError(Exception):
    pass


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than the configured cap.

    Guards against memory-exhaustion uploads. Checks Content-Length first
    (cheap path) and counts streamed bytes for chunked bodies.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        cap = get_settings().max_request_body_bytes
        if cap <= 0:
            return await call_next(request)
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > cap:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "request body is too large"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "invalid content length"}
                )
        if declared is None:
            received = 0

            async def limited_receive():  # type: ignore[no-untyped-def]
                nonlocal received
                message = await request.receive()
                chunk = message.get("body", b"")
                received += len(chunk)
                if received > cap:
                    raise _BodyTooLargeError
                return message

            request = Request(request.scope, limited_receive)
        try:
            return await call_next(request)
        except _BodyTooLargeError:
            return JSONResponse(
                status_code=413, content={"detail": "request body is too large"}
            )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        supplied_request_id = request.headers.get("X-Request-ID")
        request_id = (
            supplied_request_id
            if supplied_request_id and _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(metadata_router)
app.include_router(records_router)
app.include_router(lookup_router)
app.include_router(audit_router)
app.include_router(financial_router)
app.include_router(workflow_router)
app.include_router(construction_router)
