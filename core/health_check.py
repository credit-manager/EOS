"""
EOS Enhanced Health Check — Deep health with real checks.
P63.6: Enhanced Health Checks (API + PostgreSQL + disk + dependencies).

Replaces the simple /health endpoint with /health/full that checks:
- PostgreSQL connectivity
- Disk space
- Memory usage
- Process health
- Dependencies
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Response
from sqlalchemy import text

logger = logging.getLogger("eos.health")

router = APIRouter(tags=["Health"], include_in_schema=False)


def _check_database() -> dict[str, Any]:
    """Check PostgreSQL connectivity and stats."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        start = time.time()
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)
        db.close()

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "message": "PostgreSQL responding"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "PostgreSQL unreachable"
        }


def _check_disk() -> dict[str, Any]:
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
            "message": message
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e),
            "message": "Could not check disk"
        }


def _check_memory() -> dict[str, Any]:
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
            "message": message
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e),
            "message": "Could not check memory"
        }


def _check_process() -> dict[str, Any]:
    """Check FastAPI process health."""
    try:
        proc = psutil.Process(os.getpid())
        mem_mb = round(proc.memory_info().rss / (1024**2), 2)
        cpu_percent = proc.cpu_percent(interval=0.1)
        threads = proc.num_threads()
        uptime_seconds = time.time() - proc.create_time()

        return {
            "status": "healthy",
            "pid": os.getpid(),
            "memory_mb": mem_mb,
            "cpu_percent": cpu_percent,
            "threads": threads,
            "uptime_hours": round(uptime_seconds / 3600, 2),
            "message": f"Process running (PID {os.getpid()})"
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e),
            "message": "Could not check process"
        }


# ═══════════════════════════════════════════════
# Health Endpoints
# ═══════════════════════════════════════════════

@router.get("/health")
async def simple_health():
    """Simple health check (load balancer compatible)."""
    return {"status": "healthy", "service": "eos-dbp", "version": "1.0.0"}


@router.get("/health/full")
async def full_health(response: Response):
    """
    Full health check with real component verification.
    Returns HTTP 200 if all critical components OK, 503 if any critical fails.
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

    # Determine overall status
    critical_checks = ["api", "database"]
    overall_status = "healthy"

    for check_name, check_result in checks.items():
        if check_result.get("status") == "unhealthy":
            if check_name in critical_checks:
                overall_status = "degraded"
                response.status_code = 503
            else:
                if overall_status == "healthy":
                    overall_status = "degraded"
        elif check_result.get("status") == "critical":
            overall_status = "critical"
            response.status_code = 503

    return {
        "status": overall_status,
        "service": "eos-dbp",
        "version": "1.0.0",
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
    if db_check["status"] == "unhealthy":
        response.status_code = 503
        return {"status": "not_ready", "reason": db_check["message"]}
    return {"status": "ready"}