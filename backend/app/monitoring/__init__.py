"""Monitoring and alerting — health dashboard endpoint."""
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

_start_time = time.monotonic()


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Comprehensive health check for monitoring."""
    uptime = time.monotonic() - _start_time
    db_ok = True
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 1),
        "checks": {
            "database": "ok" if db_ok else "error",
            "api": "ok",
        },
    }


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    """System metrics for monitoring."""
    from ...audit.models import AuditEvent
    from ...events.models import Event

    try:
        event_count = db.query(Event).count()
    except Exception:
        event_count = 0

    try:
        audit_count = db.query(AuditEvent).count()
    except Exception:
        audit_count = 0

    return {
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "events_total": event_count,
        "audit_events_total": audit_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/security-audit")
def security_audit(db: Session = Depends(get_db)) -> dict:
    """Run a security audit and return results."""
    from ..security_audit import run_security_audit
    return run_security_audit(db)
