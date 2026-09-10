"""
EOS / 2TO ERP Platform — single canonical application entrypoint.

The repository is one deployable project. The root application remains the
compatibility/runtime surface while eos_v2 is treated as an internal bounded
architecture being integrated into this same application, not as a second
standalone product.
"""

# The existing production runtime is intentionally retained during convergence:
# it contains the broadest verified module/API surface. New capabilities should
# be implemented in the canonical architecture and exposed through this app.
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
import uuid

from core.structured_logging import setup_logging, RequestIdMiddleware, audit_logger
from core.locale_middleware import LocaleMiddleware
from core.audit import set_request_id
from core.health_check import router as health_router
from core.api_versioning import APIVersionMiddleware, SUPPORTED_VERSIONS
from core.auth import get_current_user, require_permission

from routers import (
    dynamic_crud, relationships, entity_management, events_webhooks,
    security_admin, auto_ui, notifications, dashboards, workflows, data_jobs,
    webhook_management, validation, erp_foundation, accounting, finance,
    procurement, inventory, sales, sales_api, inventory_api, accounting_api,
    projects_api, hr_api, control_plane, construction_api, industry_framework,
    trading_api, retail_api, restaurant_api, manufacturing_api, services_api,
    notify_api, approve_api, docs_api, analytics_api, custom_api, hr, projects,
    fixed_assets, documents, audit, localization, esignature, api_quotas,
    reports, ai_features, system, production_ops, validation_ops, saas_cp,
    tenant_lifecycle, billing, edge_region, analytics, compliance, identity,
    iot, blockchain, platform_maturity, onboarding, ai_composer, builder,
    marketplace, billing_flow, portal, saas_journey, auth as auth_router,
    locale_router, analytics_router, whitelabel, ws_router, two_factor_api,
    payment_api, currency_api, reconciliation_api, portal_customer_api,
    reporting_api,
)

MAX_BODY_BYTES = int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024)))


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return Response(
                content='{"status":"error","error":{"code":"PAYLOAD_TOO_LARGE","message":"Request body exceeds size limit"}}',
                status_code=413,
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
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers.pop("server", None)
        return response


async def require_sales_api_permission(request: Request, user: dict = Depends(get_current_user)):
    action = {"GET": "read", "HEAD": "read", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(request.method.upper())
    if action is None:
        raise HTTPException(status_code=405, detail="Method not allowed")
    return await require_permission("dynamic", action)(user)


setup_logging()

app = FastAPI(
    title="2TO ERP Platform",
    description="Single-project, multi-tenant ERP platform with dynamic metadata, accounting, workflow, AI and industry capabilities.",
    version="2.0.0",
    docs_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/docs",
    redoc_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/redoc",
)

cors_origins = json.loads(os.getenv("EOS_CORS_ORIGINS", "[]"))
if not cors_origins:
    cors_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-ID"], expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"])

allowed_hosts = [host.strip() for host in os.getenv("EOS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
auth_mode = os.getenv("EOS_AUTH_MODE", "test").lower()
if auth_mode == "production" or os.getenv("EOS_TRUSTED_HOSTS_ENABLED", "false").lower() == "true":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LocaleMiddleware)
app.add_middleware(APIVersionMiddleware)


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    from prometheus_client import generate_latest, CollectorRegistry, ProcessCollector, PlatformCollector
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    return Response(content=generate_latest(registry), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/api/version", tags=["System"])
async def api_version():
    return {"status": "success", "data": {"current_version": "v1", "supported_versions": list(SUPPORTED_VERSIONS.keys()), "versions": SUPPORTED_VERSIONS, "versioning": {"url_prefix": "/api/{version}/...", "header": "Accept-Version: v1", "default": "v1"}}}


for router, dependencies in (
    (dynamic_crud.router, None), (relationships.router, None), (entity_management.router, None),
    (events_webhooks.router, None), (security_admin.router, None), (auto_ui.router, None),
    (notifications.router, None), (dashboards.router, None), (workflows.router, None),
    (data_jobs.router, None), (webhook_management.router, None), (validation.router, None),
    (erp_foundation.router, None), (accounting.router, None), (finance.router, None),
    (procurement.router, None), (inventory.router, None), (sales.router, None),
    (sales_api.router, [Depends(require_sales_api_permission)]), (inventory_api.router, None),
    (accounting_api.router, None), (projects_api.router, None), (hr_api.router, None),
    (control_plane.router, None), (construction_api.router, None), (industry_framework.router, None),
    (trading_api.router, None), (retail_api.router, None), (restaurant_api.router, None),
    (manufacturing_api.router, None), (services_api.router, None), (notify_api.router, None),
    (approve_api.router, None), (docs_api.router, None), (analytics_api.router, None),
    (custom_api.router, None), (hr.router, None), (projects.router, None), (fixed_assets.router, None),
    (documents.router, None), (audit.router, None), (localization.router, None), (esignature.router, None),
    (api_quotas.router, None), (reports.router, None), (ai_features.router, None), (system.router, None),
    (production_ops.router, None), (validation_ops.router, None), (saas_cp.router, None),
    (tenant_lifecycle.router, None), (billing.router, None), (edge_region.router, None),
    (analytics.router, None), (compliance.router, None), (identity.router, None), (iot.router, None),
    (blockchain.router, None), (platform_maturity.router, None), (onboarding.router, None),
    (ai_composer.router, None), (builder.router, None), (marketplace.router, None),
    (billing_flow.router, None), (portal.router, None), (saas_journey.router, None),
    (auth_router.router, None), (locale_router.router, None), (analytics_router.router, None),
    (whitelabel.router, None), (ws_router.router, None), (two_factor_api.router, None),
    (payment_api.router, None), (currency_api.router, None), (reconciliation_api.router, None),
    (portal_customer_api.router, None), (reporting_api.router, None),
):
    app.include_router(router, dependencies=dependencies or [])

app.include_router(health_router)


@app.on_event("startup")
async def validate_configuration():
    errors = []
    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL not set")
    if auth_mode == "production" and not os.getenv("EOS_SECRET_KEY"):
        errors.append("EOS_SECRET_KEY required in production mode")
    if errors:
        print(f"CONFIGURATION ERRORS: {', '.join(errors)}")
        if auth_mode == "production":
            raise RuntimeError("Blocking production startup due to invalid configuration")
    else:
        print(f"Configuration OK: auth_mode={auth_mode}")
    audit_logger.log_event(event="platform_startup", details={"auth_mode": auth_mode, "version": "2.0.0"})


@app.on_event("shutdown")
async def graceful_shutdown():
    import logging
    try:
        from database import engine
        engine.dispose()
    except Exception as exc:
        logging.getLogger("eos.shutdown").warning("Error disposing engine: %s", exc)
    audit_logger.log_event(event="platform_shutdown", details={"version": "2.0.0"})


# Canonical frontend: /frontend is the only source/artifact location.
_REACT_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_REACT_DIST):
    assets_dir = os.path.join(_REACT_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/ui/assets", StaticFiles(directory=assets_dir), name="react-assets")
    icons_dir = os.path.join(_REACT_DIST, "icons")
    if os.path.isdir(icons_dir):
        app.mount("/ui/icons", StaticFiles(directory=icons_dir), name="react-icons")

    @app.get("/ui/manifest.webmanifest", include_in_schema=False)
    async def serve_manifest():
        return FileResponse(os.path.join(_REACT_DIST, "manifest.webmanifest"), media_type="application/manifest+json")

    @app.get("/ui/sw.js", include_in_schema=False)
    async def serve_sw():
        return FileResponse(os.path.join(_REACT_DIST, "sw.js"), media_type="application/javascript")

    @app.get("/ui/{full_path:path}", include_in_schema=False)
    async def serve_react(full_path: str):
        return FileResponse(os.path.join(_REACT_DIST, "index.html"), media_type="text/html")


@app.get("/")
async def root():
    index_path = os.path.join(_REACT_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "2TO ERP Platform is running", "version": "2.0.0", "docs": "/docs", "health": "/health", "ui": "/ui"}


@app.get("/app")
async def serve_landing():
    index_path = os.path.join(_REACT_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Frontend artifact not found", "ui": "/ui"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
