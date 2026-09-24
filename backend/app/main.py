import asyncio
import logging
import os
import re
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .ai.router import router as ai_router
from .api_version import APIVersionMiddleware
from .audit.router import router as audit_router
from .auth.router import router as auth_router
from .billing.router import router as billing_router
from .billing.payment_router import router as payment_router
from .builder.router import router as builder_router
from .cache import ResponseCacheMiddleware
from .compression import ResponseCompressionMiddleware
from .config import get_settings
from .construction.router import router as construction_router
from .construction.pack_router import router as construction_pack_router
from .db import Base, engine
from .documents.router import router as documents_router
from .error_handlers import setup_error_handlers
from .events.router import router as events_router
from .export_router import router as export_router
from .financial.router import router as financial_router
from .graph.router import router as graph_router
from .ai.governance.router import router as governance_router
from .ai.governance.limits_router import router as limits_router
from .globalization.router import router as globalization_router
from .integrations.connector_routes import router as connector_router
from .integrations.router import router as integrations_router
from .health import router as health_router
from .logging_config import setup_logging, setup_structured_logging
from .lookup.router import router as lookup_router
from .marketplace.router import router as marketplace_router
from .metadata.router import router as metadata_router
from .metrics import increment_error_count, increment_request_count
from .metrics import router as metrics_router
from .monitoring import router as monitoring_router
from .notification.router import router as notification_router
from .permissions_router import router as permissions_router
from .policy.router import router as policy_router
from .admin_router import router as admin_router
from .feature_flags.router import router as feature_flags_router
from .query_logger import setup_query_logging
from .query_optimizer import setup_query_optimization
from .rbac import RBACMiddleware
from .rate_limiter import (
    AdvancedRateLimitMiddleware,
    RateLimitRule,
    TenantRateLimitMiddleware,
    reset_rate_limiters,
)
from .records.router import router as records_router
from .redis_client import close_redis, get_redis
from .reporting.router import router as analytics_router
from .reports_router import router as reports_router
from .request_logger import RequestResponseLoggingMiddleware
from .request_validator import RequestValidationMiddleware
from .rules import engine as rules_engine
from .rules.router import router as rules_router
from .retail.router import router as retail_router
from .manufacturing.router import router as manufacturing_router
from .sdk.router import router as sdk_router
from .security_headers import SecurityHeadersMiddleware
from .tenant_isolation import TenantIsolationMiddleware
from .settings.router import router as settings_router
from .websocket import router as websocket_router
from .workflow.router import router as workflow_router

logger = logging.getLogger("2to-eos")

settings = get_settings()
setup_structured_logging(settings.app_env)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))


def reset_rate_limit_state() -> None:
    """Clear all rate limit counters (Redis-backed and in-memory)."""
    _RATE_LIMIT_STATE.clear()
    reset_rate_limiters()
    try:
        redis = get_redis()
        for key in redis.scan_iter(match="rate_limit:*"):
            redis.delete(key)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from .monitoring.sentry import init_sentry
    init_sentry()

    logger.info("Starting up %s v%s", settings.app_name, settings.app_version)

    if settings.app_env != "production" and not _IS_VERCEL:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (dev mode)")

    setup_query_logging(engine)
    logger.info("Query logging enabled")

    setup_query_optimization(engine)
    logger.info("Query optimization enabled")

    try:
        import backend.app.query_monitor  # noqa: F401
        logger.info("Query performance monitor enabled")
    except Exception as exc:
        logger.warning("Query monitor setup skipped: %s", exc)

    try:
        get_redis()
        logger.info("Redis connection established")
    except Exception as exc:
        logger.warning("Redis connection failed: %s", exc)

    # Initialize Egypt Pack (Globalization Engine - first country pack)
    try:
        from .globalization.pack_registry import initialize_pack
        from .db import SessionLocal
        db_session = SessionLocal()
        try:
            eg_result = initialize_pack("EG", db_session)
            logger.info(
                "Egypt Pack initialized via registry: country=%s, currency=%s, pack=%s, tax_configs=%d",
                eg_result["country"].code if eg_result.get("country") else None,
                eg_result["currency"].code if eg_result.get("currency") else None,
                eg_result["pack"].pack_version if eg_result.get("pack") else None,
                len(eg_result.get("tax_configs", [])),
            )
        finally:
            db_session.close()
    except Exception as exc:
        logger.warning("Egypt Pack initialization skipped: %s", exc)

    # Initialize Saudi Arabia Pack (Globalization Engine - second country pack)
    try:
        from .globalization.pack_registry import initialize_pack
        from .db import SessionLocal
        db_session = SessionLocal()
        try:
            sa_result = initialize_pack("SA", db_session)
            logger.info(
                "KSA Pack initialized via registry: country=%s, currency=%s, pack=%s, tax_configs=%d",
                sa_result["country"].code if sa_result.get("country") else None,
                sa_result["currency"].code if sa_result.get("currency") else None,
                sa_result["pack"].pack_version if sa_result.get("pack") else None,
                len(sa_result.get("tax_configs", [])),
            )
        finally:
            db_session.close()
    except Exception as exc:
        logger.warning("KSA Pack initialization skipped: %s", exc)

    yield

    logger.info("Shutting down %s", settings.app_name)
    close_redis()
    logger.info("Redis connection closed")
    logger.info("Shutdown complete")


_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RATE_LIMIT_TRACKED_ROUTES = frozenset({"POST:/api/v1/auth/token", "POST:/api/v1/auth/register"})
_RATE_LIMIT_STATE: dict[tuple[str, str], deque] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter for authentication endpoints.

    Defends /auth/token and /auth/register against credential stuffing
    and brute force. Uses Redis for shared state across workers and falls
    back to an in-process sliding window when Redis is unavailable.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        route_key = f"{request.method}:{request.url.path}"
        if route_key not in _RATE_LIMIT_TRACKED_ROUTES:
            return await call_next(request)
        limit = get_settings().rate_limit_auth_per_minute
        if limit <= 0:
            return await call_next(request)
        client = request.client.host if request.client is not None else "unknown"
        now = time.monotonic()

        def blocked() -> Response:
            reset_time = int(time.time() + _RATE_LIMIT_WINDOW_SECONDS)
            return JSONResponse(
                status_code=429,
                content={"detail": "too many authentication attempts, try again later"},
                headers={
                    "Retry-After": str(max(1, int(_RATE_LIMIT_WINDOW_SECONDS))),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        try:
            r = get_redis()
            pipe = r.pipeline()
            bucket_key = f"rate_limit:{client}:{route_key}"
            pipe.zremrangebyscore(bucket_key, 0, time.time() - _RATE_LIMIT_WINDOW_SECONDS)
            pipe.zadd(bucket_key, {str(time.time()): time.time()})
            pipe.zcard(bucket_key)
            pipe.expire(bucket_key, int(_RATE_LIMIT_WINDOW_SECONDS))
            results = pipe.execute()
            request_count = results[2]
            if request_count > limit:
                return blocked()
            response = await call_next(request)
            remaining = max(0, limit - request_count)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + _RATE_LIMIT_WINDOW_SECONDS))
            return response
        except Exception:
            bucket_key = (client, route_key)
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
                return blocked()
            bucket.append(now)
            response = await call_next(request)
            remaining = max(0, limit - len(bucket))
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + _RATE_LIMIT_WINDOW_SECONDS))
            return response


class _BodyTooLargeError(Exception):
    pass


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce a maximum request processing time.

    Prevents long-running requests from consuming resources indefinitely.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        timeout_seconds = 30
        try:
            response = await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
            return response
        except TimeoutError:
            logger.warning(
                "Request timeout: %s %s (limit: %ds)",
                request.method,
                request.url.path,
                timeout_seconds,
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timeout"},
            )


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

        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                logger.warning("Blocked request from unauthorized origin: %s", origin)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "origin not allowed"},
                )

        start_time = time.monotonic()
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            "[%s] %s %s from %s",
            request_id[:8],
            request.method,
            request.url.path,
            client_host,
        )

        response = await call_next(request)

        increment_request_count()

        if response.status_code >= 400:
            increment_error_count()

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "[%s] %s %s -> %d (%.1fms)",
            request_id[:8],
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id

        if request.url.path.startswith("/api/v1/"):
            if request.url.path in ("/api/v1/health", "/api/v1/version"):
                response.headers["Cache-Control"] = "public, max-age=60"
            elif request.method == "GET":
                response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
            else:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        return response


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="2TO EOS is an AI-native, metadata-driven ERP platform for emerging markets.",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication and user management operations",
        },
        {
            "name": "metadata",
            "description": "Metadata entity definition and management",
        },
        {
            "name": "records",
            "description": "Dynamic record CRUD operations",
        },
        {
            "name": "lookup",
            "description": "Entity lookup and search operations",
        },
        {
            "name": "audit",
            "description": "Audit trail and event logging",
        },
        {
            "name": "financial",
            "description": "Financial accounting and journal entries",
        },
        {
            "name": "workflow",
            "description": "Workflow definitions and approval processes",
        },
        {
            "name": "construction",
            "description": "Construction project management",
        },
        {
            "name": "events",
            "description": "Platform event bus: publish and consume first-class domain events",
        },
        {
            "name": "rules",
            "description": "Rules engine (WHEN/IF/THEN): programmable business policies",
        },
        {
            "name": "graph",
            "description": "Business Graph: entity story across related business objects",
        },
        {
            "name": "analytics",
            "description": "Analytics Engine: saved KPI reports, drill-to-source refs, and the Workspace home feed",
        },
        {
            "name": "system",
            "description": "System health and version information",
        },
        {"name": "billing", "description": "Subscription plans, billing, and invoices"},
        {"name": "monitoring", "description": "System health, metrics, and security audit"},
        {"name": "builder", "description": "Business Object builder and customization"},
        {"name": "ai", "description": "AI copilot, agents, and governance"},
        {"name": "documents", "description": "Document intelligence, OCR, and classification"},
        {"name": "integrations", "description": "External system connectors and webhooks"},
        {"name": "globalization", "description": "Country packs, currencies, and compliance"},
        {"name": "sdk", "description": "Developer SDK and API access"},
        {"name": "marketplace", "description": "Apps, plugins, and extensions"},
        {"name": "settings", "description": "Tenant settings and configuration"},
    ],
)

setup_error_handlers(app)

from .api_docs import configure_api_docs
configure_api_docs(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantIsolationMiddleware)
app.add_middleware(APIVersionMiddleware)
app.add_middleware(RBACMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(ResponseCacheMiddleware)
app.add_middleware(AdvancedRateLimitMiddleware, rules={
    "default": RateLimitRule(max_requests=100, window_seconds=60),
    "auth": RateLimitRule(max_requests=settings.rate_limit_auth_per_minute, window_seconds=60),
    "write": RateLimitRule(max_requests=30, window_seconds=60),
})
app.add_middleware(TenantRateLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTimeoutMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(ResponseCompressionMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,
)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(metadata_router)
app.include_router(records_router)
app.include_router(lookup_router)
app.include_router(marketplace_router)
app.include_router(audit_router)
app.include_router(financial_router)
app.include_router(workflow_router)
app.include_router(construction_router)
app.include_router(construction_pack_router)
app.include_router(notification_router)
app.include_router(events_router)
app.include_router(rules_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "demo": "http://localhost:5173",
    }
app.include_router(graph_router)
app.include_router(analytics_router)
app.include_router(export_router)
app.include_router(reports_router)
app.include_router(permissions_router)
app.include_router(policy_router)
app.include_router(admin_router)
app.include_router(feature_flags_router)
app.include_router(ai_router)
app.include_router(governance_router)
app.include_router(limits_router)
app.include_router(documents_router)
app.include_router(integrations_router)
app.include_router(globalization_router)
app.include_router(builder_router)
app.include_router(retail_router)
app.include_router(manufacturing_router)
app.include_router(sdk_router)
app.include_router(settings_router)
app.include_router(websocket_router)
app.include_router(monitoring_router)
app.include_router(billing_router)
app.include_router(payment_router)

rules_engine.install_listener()
