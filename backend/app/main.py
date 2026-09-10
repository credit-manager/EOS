from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.router import router as auth_router
from .config import get_settings
from .db import Base, engine
from .health import router as health_router
from .metadata.router import router as metadata_router
from .records.router import router as records_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.5.0")

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


@app.on_event("startup")
def startup() -> None:
    if settings.app_env != "production":
        Base.metadata.create_all(bind=engine)
