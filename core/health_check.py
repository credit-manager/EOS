"""Production health endpoints with safe readiness/liveness semantics."""

import hmac
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Request, Response
from sqlalchemy import text

logger = logging.getLogger("eos.health")
router = APIRouter(tags=["Health"], include_in_schema=False)


def _check_database() -> dict[str, Any]:
    """Check PostgreSQL connectivity without exposing connection details."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        start = time.time()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"status": "healthy", "latency_ms": round((time.time() - start) * 1000, 2),
                "message": "PostgreSQL responding"}
    except Exception:
        logger.exception("Database health check failed")
        return {"status": "unhealthy", "message": "PostgreSQL unavailable"}


def _check_disk() -> dict[str, Any]:
    try:
        disk = psutil.disk_usage("/")
        percent = round(disk.percent, 1)
        free_gb = round(disk.free / (1024**3), 2)
        status = "critical" if percent > 95 else "warning" if percent > 85 else "healthy"
        return {"status": status, "percent_used": percent, "free_gb": free_gb,
                "total_gb": round(disk.total / (1024**3), 2)}
    except Exception:
        logger.exception("Disk health check failed")
        return {"status": "unknown", "message": "Disk status unavailable"}


def _check_memory() -> dict[str, Any]:
    try:
        mem = psutil.virtual_memory()
        percent = round(mem.percent, 1)
        status = "critical" if percent > 95 else "warning" if percent > 85 else "healthy"
        return {"status": status, "percent_used": percent,
                "available_gb": round(mem.available / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2)}
    except Exception:
        logger.exception("Memory health check failed")
        return {"status": "unknown", "message": "Memory status unavailable"}


def _check_process() -> dict[str, Any]:
    try:
        proc = psutil.Process(os.getpid())
        return {"status": "healthy", "memory_mb": round(proc.memory_info().rss / (1024**2), 2),
                "cpu_percent": proc.cpu_percent(interval=0.1), "threads": proc.num_threads(),
                "uptime_hours": round((time.time() - proc.create_time()) / 3600, 2)}
    except Exception:
        logger.exception("Process health check failed")
        return {"status": "unknown", "message": "Process status unavailable"}


def _full_health_allowed(request: Request) -> bool:
    if os.getenv("EOS_AUTH_MODE", "test").lower() != "production":
        return True
    expected = os.getenv("EOS_HEALTH_TOKEN", "")
    supplied = request.headers.get("x-health-token", "")
    return bool(expected and supplied and hmac.compare_digest(supplied, expected))


@router.get("/health")
async def simple_health():
    return {"status": "healthy", "service": "eos-dbp", "version": "1.0.0"}


@router.get("/health/full")
async def full_health(request: Request, response: Response):
    """Detailed health is protected in production because it exposes operational telemetry."""
    if not _full_health_allowed(request):
        response.status_code = 404
        return {"status": "not_found"}

    start = time.time()
    checks = {
        "api": {"status": "healthy", "message": "FastAPI running"},
        "database": _check_database(),
        "disk": _check_disk(),
        "memory": _check_memory(),
        "process": _check_process(),
    }
    overall_status = "healthy"
    for name, result in checks.items():
        if result.get("status") == "critical":
            overall_status = "critical"
            response.status_code = 503
        elif result.get("status") in {"unhealthy", "warning", "unknown"}:
            if overall_status == "healthy":
                overall_status = "degraded"
            if name == "database" or result.get("status") == "critical":
                response.status_code = 503

    return {"status": overall_status, "service": "eos-dbp", "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "duration_ms": round((time.time() - start) * 1000, 2)}


@router.get("/health/live")
async def liveness():
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response):
    db_check = _check_database()
    if db_check["status"] != "healthy":
        response.status_code = 503
        return {"status": "not_ready", "reason": "PostgreSQL unavailable"}
    return {"status": "ready"}
