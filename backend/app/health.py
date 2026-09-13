import time
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from .config import get_settings
from .db import check_db_health
from .redis_client import check_redis_health

router = APIRouter(prefix="/api/v1", tags=["system"])

_start_time = time.monotonic()


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "service": "2to-eos",
                    "version": "0.3.0",
                    "environment": "production",
                    "database": "connected",
                    "redis": "connected",
                    "circuit_breakers": [],
                    "uptime_seconds": 12345.67,
                    "timestamp": "2026-09-13T12:00:00Z",
                }
            ]
        }
    )

    status: str
    service: str
    version: str
    environment: str
    database: str
    redis: str
    circuit_breakers: list
    uptime_seconds: float
    timestamp: str


class VersionResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "2TO EOS",
                    "version": "0.3.0",
                }
            ]
        }
    )

    name: str
    version: str


class ReadyResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ready": True,
                    "database": True,
                    "redis": True,
                }
            ]
        }
    )

    ready: bool
    database: bool
    redis: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    uptime = time.monotonic() - _start_time
    
    db_ok = check_db_health()
    redis_ok = check_redis_health()
    
    status = "ok"
    if not db_ok:
        status = "critical"
    elif not redis_ok:
        status = "degraded"
    
    return HealthResponse(
        status=status,
        service="2to-eos",
        version=settings.app_version,
        environment=settings.app_env,
        database="connected" if db_ok else "disconnected",
        redis="connected" if redis_ok else "disconnected",
        circuit_breakers=[],
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(name=settings.app_name, version=settings.app_version)


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    db_ok = check_db_health()
    redis_ok = check_redis_health()
    return ReadyResponse(ready=db_ok and redis_ok, database=db_ok, redis=redis_ok)
