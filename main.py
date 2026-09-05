"""
EOS Dynamic Business Platform — FastAPI Application (P13 hardened)
"""
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from core.structured_logging import setup_logging, RequestIdMiddleware, audit_logger
from core.locale_middleware import LocaleMiddleware
from routers import dynamic_crud
from routers import relationships
from routers import entity_management
from routers import events_webhooks
from routers import security_admin
from routers import auto_ui
from routers import notifications
from routers import dashboards
from routers import workflows
from routers import data_jobs
from routers import webhook_management
from routers import validation
from routers import erp_foundation
from routers import accounting
from routers import finance
from routers import procurement
from routers import inventory
from routers import sales, sales_api, inventory_api, accounting_api, projects_api, hr_api, control_plane, construction_api, industry_framework, trading_api, retail_api, restaurant_api, manufacturing_api, services_api, notify_api, approve_api, docs_api, analytics_api, custom_api
from routers import hr
from routers import projects
from routers import fixed_assets
from routers import documents
from routers import audit
from routers import localization
from routers import esignature
from routers import api_quotas
from routers import reports
from routers import ai_features
from routers import system
from routers import production_ops
from routers import validation_ops
from routers import saas_cp
from routers import tenant_lifecycle
from routers import billing
from routers import edge_region
from routers import analytics
from routers import compliance
from routers import identity
from routers import iot
from routers import blockchain
from routers import platform_maturity
from routers import onboarding
from routers import ai_composer
from routers import builder
from routers import marketplace
from routers import billing_flow
from routers import portal
from routers import saas_journey
from routers import auth as auth_router
from routers import locale_router
from routers import analytics_router
from routers import whitelabel
from routers import ws_router
from routers import two_factor_api
from routers import payment_api
from routers import currency_api
from routers import reconciliation_api
from routers import portal_customer_api
from routers import reporting_api
from core.audit import set_request_id
from core.health_check import router as health_router
from core.api_versioning import APIVersionMiddleware, SUPPORTED_VERSIONS
from core.auth import get_current_user, require_permission
import os
import json
import uuid

MAX_BODY_BYTES = int(os.getenv("EOS_MAX_BODY_BYTES", str(10 * 1024 * 1024)))


class SecurityMiddleware(BaseHTTPMiddleware):
    """P13 security middleware for body size, correlation IDs and headers."""

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
        if "server" in response.headers:
            del response.headers["server"]
        return response


async def require_sales_api_permission(request: Request, user: dict = Depends(get_current_user)):
    """Apply explicit RBAC to the direct Sales CRM surface."""
    method = request.method.upper()
    action = {
        "GET": "read",
        "HEAD": "read",
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method)
    if action is None:
        raise HTTPException(status_code=405, detail="Method not allowed")
    checker = require_permission("dynamic", action)
    return await checker(user)


setup_logging()

app = FastAPI(
    title="EOS Dynamic Business Platform",
    version="1.0.0",
    docs_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/docs",
    redoc_url=None if os.getenv("EOS_DISABLE_DOCS") == "true" else "/redoc",
)

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

allowed_hosts = [host.strip() for host in os.getenv("EOS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
auth_mode = os.getenv("EOS_AUTH_MODE", "test").lower()
trusted_hosts_enabled = os.getenv("EOS_TRUSTED_HOSTS_ENABLED", "false").lower() == "true"
if auth_mode == "production" or trusted_hosts_enabled:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LocaleMiddleware)
app.add_middleware(APIVersionMiddleware)

from prometheus_client import generate_latest, CollectorRegistry
from prometheus_client import ProcessCollector, PlatformCollector

_prometheus_registry = CollectorRegistry()
ProcessCollector(registry=_prometheus_registry)
PlatformCollector(registry=_prometheus_registry)


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(content=generate_latest(_prometheus_registry), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/api/version", tags=["System"])
async def api_version():
    return {
        "status": "success",
        "data": {
            "current_version": "v1",
            "supported_versions": list(SUPPORTED_VERSIONS.keys()),
            "versions": SUPPORTED_VERSIONS,
            "versioning": {"url_prefix": "/api/{version}/...", "header": "Accept-Version: v1", "default": "v1"},
        },
    }


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
app.include_router(sales_api.router, dependencies=[Depends(require_sales_api_permission)])
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
app.include_router(reporting_api.router, prefix="/api/v1")


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
    audit_logger.log_event(event="platform_startup", details={"auth_mode": auth_mode, "version": "1.0.0"})
    print(f"Security: CORS={bool(cors_origins)}, body_limit={MAX_BODY_BYTES}, hosts={allowed_hosts}, trusted_hosts={auth_mode == 'production' or trusted_hosts_enabled}")


app.include_router(health_router)


@app.get("/")
def root():
    docs_enabled = os.getenv("EOS_DISABLE_DOCS") != "true"
    return {"message": "EOS DBP Core is running!", "docs": "/docs" if docs_enabled else None}


@app.get("/app")
async def serve_landing():
    from fastapi.responses import FileResponse
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Landing page not found", "docs": "/docs"}


# P67: the canonical frontend source and served artifact share one path.
import os as _os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as _FileResponse

_REACT_DIST = _os.path.join(_os.path.dirname(__file__), "erp-system", "frontend", "dist")

if _os.path.isdir(_REACT_DIST):
    _assets_dir = _os.path.join(_REACT_DIST, "assets")
    if _os.path.isdir(_assets_dir):
        app.mount("/ui/assets", StaticFiles(directory=_assets_dir), name="react-assets")

    _icons_dir = _os.path.join(_REACT_DIST, "icons")
    if _os.path.isdir(_icons_dir):
        app.mount("/ui/icons", StaticFiles(directory=_icons_dir), name="react-icons")

    @app.get("/ui/manifest.webmanifest")
    async def _serve_manifest():
        return _FileResponse(_os.path.join(_REACT_DIST, "manifest.webmanifest"), media_type="application/manifest+json")

    @app.get("/ui/sw.js")
    async def _serve_sw():
        return _FileResponse(_os.path.join(_REACT_DIST, "sw.js"), media_type="application/javascript")

    @app.get("/ui/{full_path:path}")
    async def _serve_react(full_path: str):
        return _FileResponse(_os.path.join(_REACT_DIST, "index.html"), media_type="text/html")

    print(f"React frontend mounted at /ui  (dist: {_REACT_DIST})")
else:
    print(f"React dist not found at {_REACT_DIST} — /ui will not be available")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
