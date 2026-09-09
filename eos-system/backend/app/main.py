"""
EOS System — Enterprise Operating System
Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.security import get_cors_origins
from app.middleware.tenant import TenantMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.api.v1 import api_router
from app.db.session import init_db
import app.models  # noqa: F401 — ensure all models are registered

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting EOS System", version=settings.VERSION)
    
    # Initialize database tables
    await init_db()
    logger.info("Database tables initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EOS System")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="EOS System API",
        description="Enterprise Operating System — ERP SaaS for Egyptian Market",
        version=settings.VERSION,
        docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan,
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom Middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantMiddleware)
    
    # Include API Router
    app.include_router(api_router, prefix="/api/v1")
    
    # Health Check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "eos-api"}
    
    # Root
    @app.get("/")
    async def root():
        return {
            "service": "EOS System API",
            "version": settings.VERSION,
            "docs": "/api/docs" if settings.ENVIRONMENT == "development" else None,
        }
    
    # Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        tb = traceback.format_exc()
        content = {
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.state.request_id if hasattr(request.state, "request_id") else None,
        }
        return JSONResponse(
            status_code=500,
            content=content
        )
    
    return app


app = create_application()
