from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eos_v2.infrastructure.db.session import Database, DatabaseConfig
from eos_v2.interfaces.api.auth import router as auth_router
from eos_v2.interfaces.api.metadata import router as metadata_router
from eos_v2.interfaces.api.records import router as records_router

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(metadata_router)
    app.include_router(records_router)

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "runtime": "v2", "status": "ok"}

    return app
