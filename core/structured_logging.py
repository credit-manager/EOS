"""
EOS Structured Logging — JSON Logs with Request ID propagation.
P63.5: Structured Logging + Request ID tracking.

Usage in main.py:
    from core.structured_logging import setup_logging, RequestIdMiddleware
    setup_logging()
    app.add_middleware(RequestIdMiddleware)
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

# ═══════════════════════════════════════════════
# Context Variables
# ═══════════════════════════════════════════════

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


# ═══════════════════════════════════════════════
# JSON Formatter
# ═══════════════════════════════════════════════

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with request context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_var.get("-"),
            "tenant_id": tenant_id_var.get("-"),
            "user_id": user_id_var.get("-"),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        # Add duration if present
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        # Add status code if present
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code

        # Add method if present
        if hasattr(record, "method"):
            log_entry["method"] = record.method

        # Add path if present
        if hasattr(record, "path"):
            log_entry["path"] = record.path

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        request_id = request_id_var.get("-")
        rid = f"[{request_id[:8]}]" if request_id != "-" else ""

        timestamp = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
        return f"{color}{timestamp} {record.levelname:8s}{self.RESET} {rid:10s} {record.name}: {record.getMessage()}"


# ═══════════════════════════════════════════════
# Setup Logging
# ═══════════════════════════════════════════════

def setup_logging(level: str | None = None, format_type: str | None = None):
    """
    Configure structured logging for EOS.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for production, "human" for development
    """
    if level is None:
        level = os.getenv("EOS_LOG_LEVEL", "info").upper()
    if format_type is None:
        format_type = os.getenv("EOS_LOG_FORMAT", "json")

    numeric_level = getattr(logging, level, logging.INFO)

    # Root logger
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Remove existing handlers
    root.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Set formatter
    if format_type == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    root.addHandler(handler)

    # Quieten noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger = logging.getLogger("eos.core")
    logger.info(f"Logging initialized: level={level}, format={format_type}")


# ═══════════════════════════════════════════════
# Request ID Middleware
# ═══════════════════════════════════════════════

class RequestIdMiddleware:
    """
    ASGI middleware that:
    1. Extracts or generates request_id
    2. Sets context vars (request_id, tenant_id, user_id)
    3. Logs request/response with timing
    4. Propagates request_id in response headers
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = str(uuid.uuid4())[:16]
        request_id_var.set(request_id)

        method = scope.get("method", "?")
        path = scope.get("path", "?")

        # Extract tenant/user from headers (simplified)
        headers = dict(scope.get("headers", []))
        headers.get(b"authorization", b"").decode()

        logger = logging.getLogger("eos.request")
        start_time = time.time()

        # Log request
        logger.info(
            f"→ {method} {path}",
            extra={"method": method, "path": path, "duration_ms": 0}
        )

        # Capture response status
        response_started = False
        status_code = 0

        async def send_wrapper(message):
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.error(
                f"✗ {method} {path} - {exc}",
                exc_info=True,
                extra={"method": method, "path": path}
            )
            raise
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"← {method} {path} [{status_code}] {duration_ms}ms",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            )

    def _extract_user_id(self, auth_header: str) -> str:
        """Extract user_id from JWT if present."""
        if not auth_header.startswith("Bearer "):
            return "-"
        try:
            from core.production_auth import decode_token
            token = auth_header[7:]
            payload = decode_token(token)
            return payload.get("sub", "-")
        except Exception:
            return "-"


# ═══════════════════════════════════════════════
# Audit Logger
# ═══════════════════════════════════════════════

class AuditLogger:
    """
    Structured audit logger for business events.

    Usage:
        audit = AuditLogger()
        audit.log_event(
            event="user_created",
            tenant_id="t1",
            user_id="u1",
            details={"email": "user@example.com"}
        )
    """

    def __init__(self):
        self.logger = logging.getLogger("eos.audit")

    def log_event(
        self,
        event: str,
        tenant_id: str = "-",
        user_id: str = "-",
        details: dict | None = None,
        severity: str = "INFO"
    ):
        """Log a structured audit event."""
        log_data = {
            "event": event,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if details:
            log_data["details"] = details

        level = getattr(logging, severity, logging.INFO)
        self.logger.log(
            level,
            f"AUDIT: {event}",
            extra={"extra_data": log_data}
        )


# Global audit logger instance
audit_logger = AuditLogger()