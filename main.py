"""
EOS Dynamic Business Platform — FastAPI Application

Production security boundaries are enforced here: request sizing,
correlation IDs, security headers, CORS/host policy and protected metrics.
"""
import json
import os
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

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

MAX_BODY_BYTES = int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024)))


class SecurityMiddleware(BaseHTTPMiddleware):
    """Request-size enforcement, correlation IDs and baseline security headers."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        try:
            if content_length and int(content_length) > MAX_BODY_BYTES:
                return Response(
                    content='{"status":"error","error":{"code":"PAYLOAD_TOO_LARGE","message":"Request body exceeds size limit"}}',
                    status_code=413,
                    media_type="application/json",
                )
        except ValueError:
            return Response(
                content='{"status":"error","error":{"code":"INVALID_CONTENT_LENGTH","message":"Invalid Content-Length header"}}',
                status_code=400,
                media_type="application/json",
            )

        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(rid)
        response = await call_next(request)

        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), microphone=()"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        if "server" in response.headers:
            del response.headers["server"]
        if os.getenv("EOS_AUTH_MODE", "test").lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


setup_logging()

_docs_disabled = os.getenv("EOS_DISABLE_DOCS", "false").lower() == "true"
app = FastAPI(
    title="EOS Dynamic Business Platform",
    version="1.0.0",
    docs_url=None if _docs_disabled else "/docs",
    redoc_url=None if _docs_disabled else "/redoc",
)


_raw_cors = os.getenv("EOS_CORS_ORIGINS", "[]")
try:
    cors_origins = json.loads(_raw_cors)
except json.JSONDecodeError as exc:
    raise RuntimeError("EOS_CORS_ORIGINS must be valid JSON") from exc
if not isinstance(cors_origins, list) or any(not isinstance(origin, str) for origin in cors_origins):
    raise RuntimeError("EOS_CORS_ORIGINS must be a JSON array of origin strings")
if not cors_origins and os.getenv("EOS_AUTH_MODE", "test").lower() != "production":
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

allowed_hosts = [h.strip() for h in os.getenv("EOS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
if os.getenv("EOS_TRUSTED_HOSTS_ENABLED", "false").lower() == "true":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LocaleMiddleware)
app.add_middleware(APIVersionMiddleware)

_prometheus_registry = CollectorRegistry()
from prometheus_client import PlatformCollector, ProcessCollector

ProcessCollector(registry=_prometheus_registry)
PlatformCollector(registry=_prometheus_registry)


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(request: Request):
    if os.getenv("EOS_AUTH_MODE", "test").lower() == "production":
        expected = os.getenv("EOS_METRICS_TOKEN", "")
        supplied = request.headers.get("x-metrics-token", "")
        if not expected or not supplied or not __import__("hmac").compare_digest(supplied, expected):
            return Response(status_code=404)
    return Response(content=generate_latest(_prometheus_registry), media_type=CONTENT_TYPE_LATEST)


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
            },
        },
    }


for _router in [
    dynamic_crud, relationships, entity_management, events_webhooks, security_admin,
    auto_ui, notifications, dashboards, workflows, data_jobs, webhook_management,
    validation, erp_foundation, accounting, finance, procurement, inventory, sales,
    sales_api, inventory_api, accounting_api, projects_api, hr_api, control_plane,
    construction_api, industry_framework, trading_api, retail_api, restaurant_api,
    manufacturing_api, services_api, notify_api, approve_api, docs_api, analytics_api,
    custom_api, hr, projects, fixed_assets, documents, audit, localization, esignature,
    api_quotas, reports, ai_features, system, production_ops, validation_ops, saas_cp,
    tenant_lifecycle, billing, edge_region, analytics, compliance, identity, iot,
    blockchain, platform_maturity, onboarding, ai_composer, builder, marketplace,
    billing_flow, portal, saas_journey, auth_router, locale_router, analytics_router,
    whitelabel, ws_router, two_factor_api, payment_api, currency_api,
    reconciliation_api, portal_customer_api, reporting_api,
]:
    app.include_router(_router.router)


@app.on_event("startup")
async def validate_configuration():
    errors = []
    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL not set")

    auth_mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    if auth_mode == "production":
        from core.production_config import validate_production_config
        checks = validate_production_config()
        errors.extend(f"{name}: {status}" for name, status, critical in checks if critical and status != "OK")

    if errors:
        audit_logger.log_event(event="platform_startup_failed", details={"auth_mode": auth_mode, "errors": errors})
        if auth_mode == "production":
            raise RuntimeError("Production configuration validation failed: " + "; ".join(errors))
    else:
        audit_logger.log_event(
            event="platform_startup",
            details={"auth_mode": auth_mode, "version": "1.0.0", "cors_origins": len(cors_origins)},
        )


app.include_router(health_router)


@app.get("/")
def root():
    return {"message": "EOS DBP Core is running!", "api": "/api/v1", "docs_enabled": not _docs_disabled}


@app.get("/app")
async def serve_landing():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Landing page not found"}


_REACT_DIST = os.path.join(os.path.dirname(__file__), "eos-system", "frontend", "dist")
if os.path.isdir(_REACT_DIST):
    _assets_dir = os.path.join(_REACT_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/ui/assets", StaticFiles(directory=_assets_dir), name="react-assets")

    _icons_dir = os.path.join(_REACT_DIST, "icons")
    if os.path.isdir(_icons_dir):
        app.mount("/ui/icons", StaticFiles(directory=_icons_dir), name="react-icons")

    @app.get("/ui/manifest.webmanifest")
    async def _serve_manifest():
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(_REACT_DIST, "manifest.webmanifest"), media_type="application/manifest+json")

    @app.get("/ui/sw.js")
    async def _serve_sw():
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(_REACT_DIST, "sw.js"), media_type="application/javascript")

    @app.get("/ui/{full_path:path}")
    async def _serve_react(full_path: str):
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(_REACT_DIST, "index.html"), media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8001")), reload=False)
