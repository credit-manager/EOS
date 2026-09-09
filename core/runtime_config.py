"""Runtime configuration helpers with production-safe defaults.

The application must never silently fall back to test authentication or permissive
observability settings outside an explicit local/test environment.
"""

from __future__ import annotations

import json
import os
from typing import Final

LOCAL_ENVIRONMENTS: Final = frozenset({"development", "dev", "local", "test", "testing"})
SUPPORTED_AUTH_MODES: Final = frozenset({"test", "production"})


class RuntimeConfigurationError(ValueError):
    """Raised when an environment variable cannot be safely interpreted."""


def environment_name() -> str:
    """Return the normalized deployment environment name."""
    return os.getenv("ENVIRONMENT", "").strip().lower()


def resolve_auth_mode() -> str:
    """Resolve authentication mode without a production unsafe default.

    An explicit ``EOS_AUTH_MODE`` always wins. When omitted, test authentication is
    allowed only in a known local/test environment or when the test-only secret is
    explicitly present. Every other deployment uses production authentication.
    """
    configured = os.getenv("EOS_AUTH_MODE")
    if configured:
        mode = configured.strip().lower()
        if mode not in SUPPORTED_AUTH_MODES:
            raise RuntimeConfigurationError(
                f"Unsupported EOS_AUTH_MODE={configured!r}; expected 'test' or 'production'"
            )
        return mode

    if environment_name() in LOCAL_ENVIRONMENTS or os.getenv("EOS_TEST_SECRET_KEY"):
        return "test"
    return "production"


def parse_bool(name: str, default: bool) -> bool:
    """Parse a strict boolean environment variable."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeConfigurationError(f"{name} must be a boolean value (true/false), got {raw!r}")


def parse_positive_int(name: str, default: int) -> int:
    """Parse a strictly positive integer environment variable."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeConfigurationError(f"{name} must be greater than zero")
    return value


def cors_origins() -> list[str]:
    """Return validated CORS origins."""
    raw = os.getenv("EOS_CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:8000", "http://127.0.0.1:8000"]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeConfigurationError("EOS_CORS_ORIGINS must contain valid JSON") from exc
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise RuntimeConfigurationError("EOS_CORS_ORIGINS must be a non-empty JSON array of strings")
    origins = [item.strip().rstrip("/") for item in value if item.strip()]
    if not origins or "*" in origins:
        raise RuntimeConfigurationError("Wildcard/empty CORS origins are forbidden when credentials are enabled")
    return origins


def metrics_enabled(auth_mode: str | None = None) -> bool:
    """Disable public metrics by default in production."""
    mode = auth_mode or resolve_auth_mode()
    return parse_bool("EOS_METRICS_ENABLED", default=mode != "production")


def docs_enabled(auth_mode: str | None = None) -> bool:
    """Keep API docs convenient locally but opt-in for production."""
    mode = auth_mode or resolve_auth_mode()
    if mode == "production":
        return parse_bool("EOS_ENABLE_DOCS", default=False)
    return not parse_bool("EOS_DISABLE_DOCS", default=False)


def allowed_hosts() -> list[str]:
    """Parse the trusted host allow-list."""
    raw = os.getenv("EOS_ALLOWED_HOSTS", "localhost,127.0.0.1")
    hosts = [item.strip() for item in raw.split(",") if item.strip()]
    if not hosts:
        raise RuntimeConfigurationError("EOS_ALLOWED_HOSTS cannot be empty")
    return hosts


def request_id_or_generate(value: str | None) -> str:
    """Validate an incoming request id without allowing log/header abuse."""
    import uuid
    if not value:
        return str(uuid.uuid4())
    candidate = value.strip()
    if not candidate or len(candidate) > 128 or any(ord(ch) < 32 or ord(ch) > 126 for ch in candidate):
        return str(uuid.uuid4())
    return candidate
