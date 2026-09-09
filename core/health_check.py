"""
EOS Enhanced Health Check — Deep health with real checks.
P63.6: Enhanced Health Checks (API + PostgreSQL + disk + dependencies).

The health surface is split into lightweight liveness/readiness probes and a
full diagnostic endpoint. Diagnostic responses deliberately avoid exposing
raw exception strings or process identifiers to external callers.
"""

import os
import time
import logging
import psutil
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Response
from sqlalchemy import text

logger = logging.getLogger("eos.health")
router = APIRouter(tags=["Health"], include_in_schema=False)
VERSION = os.getenv("EOS_APP_VERSION", "1.0.0")


def _safe_component_error(message: str) -> Dict[str, Any]:
    """Return a stable diagnostic payload without leaking exception details."""
    return {"status": "unhealthy", "message": message}


def _check_database() -> Dict[str, Any]:
    """Check PostgreSQL connectivity and latency."""
    db = None
    try:
        from database import SessionLocal
        db = SessionLocal()
        start = time.time()
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "message": "PostgreSQL responding",
        }
    except Exception:
        logger.exception("Database health check failed")
        return _safe_component_error("PostgreSQL unavailable")
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.warning("Failed to close health-check database session", exc_info=True)


def _check_disk() -> Dict[str, Any]:
    """Check disk usage."""
    try:
        disk = psutil.disk_usage("/")
        percent = round(disk.percent, 1)
        free_gb = round(disk.free / (1024**3), 2)

        if percent > 95:
            status = "critical"
            message = f"Disk almost full: {percent}%"
        elif percent > 85:
            status = "warning"
            message = f"Disk usage high: {percent}%"
        else:
            status = "healthy"
            message = f"Disk OK: {percent}% used, {free_gb}GB free"

        return {
            "status": status,
            "percent_used": percent,
            "free_gb": free_gb,
            "total_gb": round(disk.total / (1024**3), 2),
            "message": message,
        }
    except Exception:
        logger.exception("Disk health check failed")
        return {"status": "unknown", "message": "Disk status unavailable"}


def _check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        mem = psutil.virtual_memory()
        percent = round(mem.percent, 1)
        available_gb = round(mem.available / (1024**3), 2)

        if percent > 95:
            status = "critical"
            message = f"Memory almost exhausted: {percent}%"
        elif percent > 85:
            status = "warning"
            message = f"Memory usage high: {percent}%"
        else:
            status = "healthy"
            message = f"Memory OK: {percent}% used, {available_gb}GB available"

        return {
            "status": status,
            "percent_used": percent,
            "available_gb": available_gb,
            "total_gb": round(mem.total / (1024**3), 2),
            "message": message,
        }
    except Exception:
        logger.exception("Memory health check failed")
        return {"status": "unknown", "message": "Memory status unavailable"}


def _check_process() -> Dict[str, Any]:
    """Check FastAPI process health without exposing its PID."""
    try:
        proc = psutil.Process(os.getpid())
        mem_mb = round(proc.memory_info().rss / (1024**2), 2)
        cpu_percent = proc.cpu_percent(interval=0.1)
        threads = proc.num_threads()
        uptime_seconds = time.time() - proc.create_time()

        return {
            "status": "healthy",
            "memory_mb": mem_mb,
            "cpu_percent": cpu_percent,
            "threads": threads,
            "uptime_hours": round(uptime_seconds / 3600, 2),
            "message": "Process running",
        }
    except Exception:
        logger.exception("Process health check failed")
        return {"status": "unknown", "message": "Process status unavailable"}


@router.get("/health")
async def simple_health():
    """Simple health check (load balancer compatible)."""
    return {"status": "healthy", "service": "eos-dbp", "version": VERSION}


@router.get("/health/full")
async def full_health(response: Response):
    """
    Full health check with real component verification.
    Returns HTTP 200 when critical components are healthy and 503 otherwise.
    """
    start = time.time()

    checks = {
        "api": {"status": "healthy", "message": "FastAPI running"},
        "database": _check_database(),
        "disk": _check_disk(),
        "memory": _check_memory(),
        "process": _check_process(),
    }

    duration_ms = round((time.time() - start) * 1000, 2)
    critical_checks = {"api", "database"}
    overall_status = "healthy"

    for check_name, check_result in checks.items():
        status = check_result.get("status")
        if status in {"unhealthy", "critical"}:
            overall_status = "critical" if status == "critical" else "degraded"
            if check_name in critical_checks or status == "critical":
                response.status_code = 503
                if status == "critical":
                    overall_status = "critical"

    return {
        "status": overall_status,
        "service": "eos-dbp",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "duration_ms": duration_ms,
    }


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe — is the process alive?"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response):
    """Kubernetes readiness probe — can it serve traffic?"""
    db_check = _check_database()
    if db_check["status"] != "healthy":
        response.status_code = 503
        return {"status": "not_ready", "reason": "database_unavailable"}
    return {"status": "ready"}
