import time
from datetime import UTC, datetime

from fastapi import APIRouter

from .config import get_settings
from .db import check_db_health
from .redis_client import check_redis_health

router = APIRouter(prefix="/api/v1", tags=["system"])

_start_time = time.monotonic()
_request_count = 0
_error_count = 0


def increment_request_count() -> None:
    global _request_count
    _request_count += 1


def increment_error_count() -> None:
    global _error_count
    _error_count += 1


@router.get("/metrics")
def metrics() -> dict:
    settings = get_settings()
    uptime = time.monotonic() - _start_time
    
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": round(uptime, 2),
        "requests_total": _request_count,
        "errors_total": _error_count,
        "error_rate": round(_error_count / max(_request_count, 1), 4),
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": check_db_health(),
            "redis": check_redis_health(),
        },
    }
