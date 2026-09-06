from __future__ import annotations

import hmac
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.middleware.trustedhost import TrustedHostMiddleware

from eos_v2.application.identity.authentication import decode_access_token
from eos_v2.application.identity.jwks import RSAKeyRing
from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.infrastructure.db.session import Database, DatabaseConfig
from eos_v2.interfaces.api.accounting import router as accounting_router
from eos_v2.interfaces.api.ai_composer import router as ai_composer_router
from eos_v2.interfaces.api.auth import router as auth_router
from eos_v2.interfaces.api.foundation import router as foundation_router
from eos_v2.interfaces.api.industry import router as industry_router
from eos_v2.interfaces.api.metadata import router as metadata_router
from eos_v2.interfaces.api.records import router as records_router
from eos_v2.interfaces.api.web import router as web_router

from .config import Settings
from .health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0-alpha.1",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )
    app.state.settings = settings
    app.state.database = Database(DatabaseConfig(settings.database_url)) if settings.database_url else None
    app.state.jwt_keyring = RSAKeyRing.generate()

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts) or ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_hardening(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid4())
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > settings.max_body_bytes:
            response = JSONResponse(status_code=413, content={"detail": "Request body too large"})
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def authenticated_tenant_context(request: Request, call_next):
        authorization = request.headers.get("Authorization", "")
        token_value = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        context_token = None
        if token_value:
            try:
                tenant_id, actor_id, _ = decode_access_token(token_value, settings.secret_key)
            except ValueError:
                pass
            else:
                context_token = set_tenant_context(TenantContext(tenant_id, actor_id))
        try:
            return await call_next(request)
        finally:
            if context_token is not None:
                reset_tenant_context(context_token)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(metadata_router)
    app.include_router(records_router)
    app.include_router(accounting_router)
    app.include_router(foundation_router)
    app.include_router(industry_router)
    app.include_router(ai_composer_router)
    app.include_router(web_router)

    metrics_app = make_asgi_app()

    @app.middleware("http")
    async def protect_metrics(request: Request, call_next):
        if request.url.path.startswith("/metrics"):
            token = request.headers.get("X-Metrics-Token", "")
            if not settings.metrics_token or not hmac.compare_digest(token, settings.metrics_token):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return await call_next(request)

    app.mount("/metrics", metrics_app)

    @app.get("/.well-known/jwks.json", tags=["auth"])
    def jwks() -> dict[str, object]:
        return app.state.jwt_keyring.jwks()

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "runtime": "v2", "status": "ok", "web": "/web"}

    return app
