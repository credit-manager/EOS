import json
import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id

        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    def __init__(self):
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "unknown"
        if not hasattr(record, "user_id"):
            record.user_id = None
        if not hasattr(record, "tenant_id"):
            record.tenant_id = None
        return True


class PerformanceFilter(logging.Filter):
    def __init__(self, slow_threshold_ms: float = 100.0):
        super().__init__()
        self.slow_threshold_ms = slow_threshold_ms

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "duration_ms") and record.duration_ms > self.slow_threshold_ms:
            record.levelname = "WARNING"
            record.levelno = logging.WARNING
        return True


class RequestLoggingFilter(logging.Filter):
    def __init__(self, skip_paths: list[str] | None = None):
        super().__init__()
        self.skip_paths = skip_paths or ["/health", "/ready", "/version"]

    def filter(self, record: Any) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for path in self.skip_paths:
                if path in record.msg:
                    return False
        return True


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if json_format:
        formatter = JSONFormatter()
    else:
        log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(log_format, datefmt=date_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    context_filter = ContextFilter()
    root_logger.addFilter(context_filter)

    performance_filter = PerformanceFilter()
    root_logger.addFilter(performance_filter)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger = logging.getLogger("2to-eos")
    logger.info("Logging initialized at %s level (json=%s)", log_level, json_format)


def setup_structured_logging(environment: str = "development") -> None:
    """Configure logging based on environment.

    - production: JSON structured logging
    - development: human-readable logging
    """
    json_format = environment == "production"
    setup_logging(
        log_level="INFO" if environment == "production" else "DEBUG",
        json_format=json_format,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"2to-eos.{name}")
