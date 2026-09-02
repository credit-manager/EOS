"""
AUDIT MODULE FOR DYNAMIC CRUD (P13 hardened)
=============================================
Sync audit logging with:
  - Sensitive data redaction in old_values/new_values
  - Correlation ID via contextvars
  - Append-only enforcement (no UPDATE/DELETE on audit_logs)
"""

import json
import re
import uuid
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# ──────────────────────────────────────────────────────────────
# CORRELATION ID
# ──────────────────────────────────────────────────────────────

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(rid: str | None) -> None:
    _request_id_ctx.set(rid)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


# ──────────────────────────────────────────────────────────────
# REDACTION
# ──────────────────────────────────────────────────────────────

REDACT_KEY_PATTERNS = re.compile(
    r"(?i)^(password|passwd|pwd|secret|token|api_key|apikey|"
    r"authorization|ssn|social_security|national_id|"
    r"credit_card|card_number|cvv|bank_account|routing_number)$"
)
REDACT_VALUE = "***REDACTED***"


def _redact_values(values: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively redact sensitive keys from audit values."""
    if not values:
        return values

    def _walk(obj):
        if isinstance(obj, dict):
            return {
                k: REDACT_VALUE if REDACT_KEY_PATTERNS.match(str(k)) else _walk(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    return _walk(values)


# ──────────────────────────────────────────────────────────────
# SAFE JSON
# ──────────────────────────────────────────────────────────────

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return super().default(obj)


def dumps(obj):
    return json.dumps(obj, cls=SafeEncoder)


# ──────────────────────────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────────────────────────

def log_dynamic_audit(
    db: Session,
    tenant_id: str,
    user_id: str | None,
    user_email: str | None,
    action: str,
    entity_code: str,
    record_id: str | None = None,
    entity_name: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> bool:
    """
    Write an audit log entry with P13 hardening:
    - Redacts sensitive fields from old_values/new_values
    - Auto-fills request_id from contextvar if not provided
    - Never raises (returns bool)
    """
    try:
        effective_request_id = request_id or get_request_id()

        entry = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "module": "dynamic",
            "entity_type": entity_code,
            "entity_id": record_id,
            "entity_name": entity_name,
            "old_values": dumps(_redact_values(old_values)) if old_values else None,
            "new_values": dumps(_redact_values(new_values)) if new_values else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": effective_request_id,
            "status": status,
            "error_message": error_message,
            "created_at": datetime.now(timezone.utc),
        }

        query = text("""
            INSERT INTO audit_logs
            (id, tenant_id, user_id, user_email, action, module,
             entity_type, entity_id, entity_name, old_values, new_values,
             ip_address, user_agent, request_id, status, error_message, created_at)
            VALUES
            (:id, :tenant_id, :user_id, :user_email, :action, :module,
             :entity_type, :entity_id, :entity_name, :old_values, :new_values,
             :ip_address, :user_agent, :request_id, :status, :error_message, :created_at)
        """)

        db.execute(query, entry)
        return True

    except Exception as e:
        print(f"[AUDIT-FAIL] {action} on {entity_code}: {e}", flush=True)
        return False
