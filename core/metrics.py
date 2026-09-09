"""
P63 Monitoring — Prometheus Metrics for FastAPI
Provides /metrics endpoint and custom business metrics.
"""
import time
import os
from functools import wraps
from typing import Callable

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse

# ═══════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════
registry = CollectorRegistry()

# ═══════════════════════════════════════════════
# HTTP Metrics
# ═══════════════════════════════════════════════
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
    registry=registry,
)

# ═══════════════════════════════════════════════
# Business Metrics
# ═══════════════════════════════════════════════
auth_logins_total = Counter(
    "auth_logins_total",
    "Total login attempts",
    ["status"],  # success, failed, blocked
    registry=registry,
)

auth_registrations_total = Counter(
    "auth_registrations_total",
    "Total user registrations",
    ["status"],  # success, failed
    registry=registry,
)

auth_verifications_total = Counter(
    "auth_verifications_total",
    "Total email verifications",
    ["status"],  # success, failed
    registry=registry,
)

active_tenants = Gauge(
    "active_tenants",
    "Number of active tenants",
    registry=registry,
)

active_users = Gauge(
    "active_users",
    "Number of active users (last 24h)",
    registry=registry,
)

entities_created_total = Counter(
    "entities_created_total",
    "Total dynamic entities created",
    ["module"],
    registry=registry,
)

marketplace_installs_total = Counter(
    "marketplace_installs_total",
    "Total marketplace items installed",
    ["item_type"],  # industry_pack, addon
    registry=registry,
)

billing_subscriptions_total = Gauge(
    "billing_subscriptions_total",
    "Total active subscriptions",
    ["plan"],
    registry=registry,
)

billing_payments_total = Counter(
    "billing_payments_total",
    "Total payment attempts",
    ["status", "provider"],  # success, failed, simulated/stripe
    registry=registry,
)

# ═══════════════════════════════════════════════
# Database Metrics
# ═══════════════════════════════════════════════
db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

db_errors_total = Counter(
    "db_errors_total",
    "Total database errors",
    ["operation", "error_type"],
    registry=registry,
)

# ═══════════════════════════════════════════════
# System Metrics
# ═══════════════════════════════════════════════
process_uptime_seconds = Gauge(
    "process_uptime_seconds",
    "Process uptime in seconds",
    registry=registry,
)

# ═══════════════════════════════════════════════
# Start time for uptime
# ═══════════════════════════════════════════════
_start_time = time.time()


def update_uptime():
    """Update process uptime gauge."""
    process_uptime_seconds.set(time.time() - _start_time)


# ═══════════════════════════════════════════════
# Middleware
# ═══════════════════════════════════════════════
async def metrics_middleware(request: Request, call_next: Callable):
    """Middleware to collect HTTP metrics."""
    # Skip metrics endpoint itself
    if request.url.path in ["/metrics", "/health"]:
        return await call_next(request)

    method = request.method
    # Normalize endpoint path (replace IDs with placeholder)
    path = request.url.path
    # Simple normalization - replace UUIDs and IDs
    import re
    path = re.sub(r"/[0-9a-f-]{36}", "/:id", path)
    path = re.sub(r"/\d+", "/:id", path)

    start_time = time.time()
    http_requests_in_progress.labels(method=method, endpoint=path).inc()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        http_requests_in_progress.labels(method=method, endpoint=path).dec()
        http_requests_total.labels(method=method, endpoint=path, status_code=status_code).inc()
        http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

    return response


# ═══════════════════════════════════════════════
# Metrics Endpoint
# ═══════════════════════════════════════════════
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    update_uptime()
    data = generate_latest(registry)
    from fastapi import Response
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
    )


# ═══════════════════════════════════════════════
# Business Metric Helpers
# ═══════════════════════════════════════════════
def record_login(status: str):
    """Record login attempt."""
    auth_logins_total.labels(status=status).inc()


def record_registration(status: str):
    """Record registration attempt."""
    auth_registrations_total.labels(status=status).inc()


def record_verification(status: str):
    """Record email verification."""
    auth_verifications_total.labels(status=status).inc()


def record_entity_created(module: str):
    """Record dynamic entity creation."""
    entities_created_total.labels(module=module).inc()


def record_marketplace_install(item_type: str):
    """Record marketplace installation."""
    marketplace_installs_total.labels(item_type=item_type).inc()


def record_payment(status: str, provider: str = "simulated"):
    """Record payment attempt."""
    billing_payments_total.labels(status=status, provider=provider).inc()


def set_active_tenants(count: int):
    """Set active tenants count."""
    active_tenants.set(count)


def set_active_users(count: int):
    """Set active users count."""
    active_users.set(count)


def set_subscriptions(plan: str, count: int):
    """Set subscription count per plan."""
    billing_subscriptions_total.labels(plan=plan).set(count)


def record_db_query(operation: str, duration: float):
    """Record database query duration."""
    db_query_duration_seconds.labels(operation=operation).observe(duration)


def record_db_error(operation: str, error_type: str):
    """Record database error."""
    db_errors_total.labels(operation=operation, error_type=error_type).inc()


def set_db_connections(count: int):
    """Set active DB connections."""
    db_connections_active.set(count)


# ═══════════════════════════════════════════════
# Decorator for timing functions
# ═══════════════════════════════════════════════
def timed(operation: str):
    """Decorator to time a function and record metric."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                record_db_error(operation, type(e).__name__)
                raise
            finally:
                record_db_query(operation, time.time() - start)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                record_db_error(operation, type(e).__name__)
                raise
            finally:
                record_db_query(operation, time.time() - start)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator