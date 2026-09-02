"""
EOS Dynamic Business Platform — FastAPI Application (P13 hardened)
"""
import json
import os
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from core.api_versioning import SUPPORTED_VERSIONS, APIVersionMiddleware
from core.audit import set_request_id
from core.health_check import router as health_router
from core.locale_middleware import LocaleMiddleware
from core.structured_logging import RequestIdMiddleware, audit_logger, setup_logging
from routers import (
    accounting,
    accounting_api,
    ai_composer,
    ai_features,
    analytics,
    analytics_api,
    analytics_router,
    api_quotas,
    approve_api,
    audit,
    auto_ui,
    billing,
    billing_flow,
    blockchain,
    builder,
    compliance,
    construction_api,
    control_plane,
    currency_api,
    custom_api,
    dashboards,
    data_jobs,
    docs_api,
    documents,
    dynamic_crud,
    edge_region,
    entity_management,
    erp_foundation,
    esignature,
    events_webhooks,
    finance,
    fixed_assets,
    hr,
    hr_api,
    identity,
    industry_framework,
    inventory,
    inventory_api,
    iot,
    locale_router,
    localization,
    manufacturing_api,
    marketplace,
    notifications,
    notify_api,
    onboarding,
    payment_api,
    platform_maturity,
    portal,
    portal_customer_api,
    procurement,
    production_ops,
    projects,
    projects_api,
    reconciliation_api,
    relationships,
    reporting_api,
    reports,
    restaurant_api,
    retail_api,
    saas_cp,
    saas_journey,
    sales,
    sales_api,
    security_admin,
    services_api,
    system,
    tenant_lifecycle,
    trading_api,
    two_factor_api,
    validation,
    validation_ops,
    webhook_management,
    whitelabel,
    workflows,
    ws_router,
)
from routers import auth as auth_router

# ──────────────────────────────────────────────────────────────
# SECURITY MIDDLEWARE — Headers + Request ID + Body Size
# ──────────────────────────────────────────────────────────────

MAX_BODY_BYTES = int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024)))  # 10 MB default


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    P13 security middleware:
    1. Enforces max request body size (413 if exceeded)
    2. Generates/echoes X-Request-ID correlation
    3. Adds security response headers
    4. Suppresses Server header
    """

    async def dispatch(self, request: Request, call_next):
        print(f">>> SECURITY MIDDLEWARE: {request.url.path!r} <<<", flush=True)
        # 1. Body size check
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return Response(
                content='{"status":"error","error":{"code":"PAYLOAD_TOO_LARGE",'
                        '"message":"Request body exceeds size limit"}}',
                status_code=413,
                media_type="application/json",
            )

        # 2. Request ID correlation
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(rid)

        # 3. Process request
        print(f">>> SECURITY MIDDLEWARE CALLING NEXT: {request.url.path!r} <<<", flush=True)
        response = await call_next(request)
        print(f">>> SECURITY MIDDLEWARE RESPONSE: {request.url.path!r} status={response.status_code} <<<", flush=True)

        # 4. Security headers
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), microphone=()"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # Remove Server header if present
        if "server" in response.headers:
            del response.headers["server"]

        return response


# ──────────────────────────────────────────────────────────────
# APPLICATION
# ──────────────────────────────────────────────────────────────

# Initialize structured logging
setup_logging()

app = FastAPI(
    title="EOS Dynamic Business Platform",
    version="1.0.0",
    docs_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/docs",
    redoc_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/redoc",
)

# CORS
cors_origins = json.loads(os.getenv("EOS_CORS_ORIGINS", "[]"))
if not cors_origins:
    cors_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Trusted hosts
allowed_hosts = os.getenv("EOS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
if os.getenv("EOS_TRUSTED_HOSTS_ENABLED", "false").lower() == "true":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Security middleware (headers, body size, request ID)
app.add_middleware(SecurityMiddleware)

# Structured logging middleware (request_id propagation + timing)
app.add_middleware(RequestIdMiddleware)

# Locale middleware (RTL/LTR, Accept-Language, X-Locale header)
app.add_middleware(LocaleMiddleware)

# API Version middleware (v1/v2 support, Accept-Version header)
app.add_middleware(APIVersionMiddleware)

# Prometheus metrics - manual endpoint
from prometheus_client import CollectorRegistry, generate_latest

_prometheus_registry = CollectorRegistry()
# Add default collectors
from prometheus_client import PlatformCollector, ProcessCollector

ProcessCollector(registry=_prometheus_registry)
PlatformCollector(registry=_prometheus_registry)

@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(
        content=generate_latest(_prometheus_registry),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/api/version", tags=["System"])
async def api_version():
    return {
        "status": "success",
        "data": {
            "current_version": "v1",
            "supported_versions": list(SUPPORTED_VERSIONS.keys()),
            "versions": SUPPORTED_VERSIONS,
            "versioning": {
                "url_prefix": "/api/{version}/...",
                "header": "Accept-Version: v1",
                "default": "v1",
            }
        }
    }

# Routers
app.include_router(dynamic_crud.router)
app.include_router(relationships.router)
app.include_router(entity_management.router)
app.include_router(events_webhooks.router)
app.include_router(security_admin.router)
app.include_router(auto_ui.router)
app.include_router(notifications.router)
app.include_router(dashboards.router)
app.include_router(workflows.router)
app.include_router(data_jobs.router)
app.include_router(webhook_management.router)
app.include_router(validation.router)
app.include_router(erp_foundation.router)
app.include_router(accounting.router)
app.include_router(finance.router)
app.include_router(procurement.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(sales_api.router)
app.include_router(inventory_api.router)
app.include_router(accounting_api.router)
app.include_router(projects_api.router)
app.include_router(hr_api.router)
app.include_router(control_plane.router)
app.include_router(construction_api.router)
app.include_router(industry_framework.router)
app.include_router(trading_api.router)
app.include_router(retail_api.router)
app.include_router(restaurant_api.router)
app.include_router(manufacturing_api.router)
app.include_router(services_api.router)
app.include_router(notify_api.router)
app.include_router(approve_api.router)
app.include_router(docs_api.router)
app.include_router(analytics_api.router)
app.include_router(custom_api.router)
app.include_router(hr.router)
app.include_router(projects.router)
app.include_router(fixed_assets.router)
app.include_router(documents.router)
app.include_router(audit.router)
app.include_router(localization.router)
app.include_router(esignature.router)
app.include_router(api_quotas.router)
app.include_router(reports.router)
app.include_router(ai_features.router)
app.include_router(system.router)
app.include_router(production_ops.router)
app.include_router(validation_ops.router)
app.include_router(saas_cp.router)
app.include_router(tenant_lifecycle.router)
app.include_router(billing.router)
app.include_router(edge_region.router)
app.include_router(analytics.router)
app.include_router(compliance.router)
app.include_router(identity.router)
app.include_router(iot.router)
app.include_router(blockchain.router)
app.include_router(platform_maturity.router)
app.include_router(onboarding.router)
app.include_router(ai_composer.router)
app.include_router(builder.router)
app.include_router(marketplace.router)
app.include_router(billing_flow.router)
app.include_router(portal.router)
app.include_router(saas_journey.router)
app.include_router(auth_router.router)
app.include_router(locale_router.router)
app.include_router(analytics_router.router)
app.include_router(whitelabel.router)
app.include_router(ws_router.router)
app.include_router(two_factor_api.router)
app.include_router(payment_api.router)
app.include_router(currency_api.router)
app.include_router(reconciliation_api.router)
app.include_router(portal_customer_api.router)
app.include_router(reporting_api.router)


@app.on_event("startup")
async def validate_configuration():
    errors = []

    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL not set")

    auth_mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    if auth_mode == "production":
        if not os.getenv("EOS_SECRET_KEY"):
            errors.append("EOS_SECRET_KEY required in production mode")
        algo = os.getenv("EOS_ALGORITHM", "HS256")
        if algo == "HS256":
            print("WARNING: HS256 algorithm. Consider RS256 for production.")

        from core.production_config import validate_production_config
        checks = validate_production_config()
        critical = [(n, s) for n, s, c in checks if c and s != "OK"]
        if critical:
            for name, status in critical:
                errors.append(f"{name}: {status}")

    if errors:
        print(f"CONFIGURATION ERRORS: {', '.join(errors)}")
        if auth_mode == "production":
            print("BLOCKING STARTUP — Fix configuration errors before serving traffic.")
            import sys
            sys.exit(1)
    else:
        print(f"Configuration OK: auth_mode={auth_mode}")
    audit_logger.log_event(
        event="platform_startup",
        details={"auth_mode": auth_mode, "version": "1.0.0"}
    )

    print(f"Security: CORS={bool(cors_origins)}, "
          f"body_limit={MAX_BODY_BYTES}, "
          f"hosts={allowed_hosts}")


# Include enhanced health check routes (/health, /health/full, /health/live, /health/ready)
app.include_router(health_router)


@app.get("/")
def root():
    return {
        "message": "EOS DBP Core is running!",
        "docs": "/docs"
    }


@app.get("/app")
async def serve_landing():
    import os

    from fastapi.responses import FileResponse
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Landing page not found", "docs": "/docs"}


# ──────────────────────────────────────────────────────────────
# P67: React Frontend — served from eos-system/frontend/dist
# Access at http://HOST/ui  (does NOT touch /app or any API route)
# ──────────────────────────────────────────────────────────────
import os as _os

from fastapi.responses import FileResponse as _FileResponse
from fastapi.staticfiles import StaticFiles

_REACT_DIST = _os.path.join(_os.path.dirname(__file__), "eos-system", "frontend", "dist")

if _os.path.isdir(_REACT_DIST):
    # Serve JS/CSS/icons under /ui/assets/*
    _assets_dir = _os.path.join(_REACT_DIST, "assets")
    if _os.path.isdir(_assets_dir):
        app.mount("/ui/assets", StaticFiles(directory=_assets_dir), name="react-assets")

    # Serve PWA icons under /ui/icons/*
    _icons_dir = _os.path.join(_REACT_DIST, "icons")
    if _os.path.isdir(_icons_dir):
        app.mount("/ui/icons", StaticFiles(directory=_icons_dir), name="react-icons")

    # Serve manifest + service-worker at /ui/*
    @app.get("/ui/manifest.webmanifest")
    async def _serve_manifest():
        return _FileResponse(_os.path.join(_REACT_DIST, "manifest.webmanifest"),
                             media_type="application/manifest+json")

    @app.get("/ui/sw.js")
    async def _serve_sw():
        return _FileResponse(_os.path.join(_REACT_DIST, "sw.js"),
                             media_type="application/javascript")

    # Catch-all: any /ui/* that isn't an API or static file → index.html (SPA routing)
    @app.get("/ui/{full_path:path}")
    async def _serve_react(full_path: str):
        return _FileResponse(_os.path.join(_REACT_DIST, "index.html"),
                             media_type="text/html")

    print(f"React frontend mounted at /ui  (dist: {_REACT_DIST})")
else:
    print(f"React dist not found at {_REACT_DIST} — /ui will not be available")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
