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
from datetime import date, datetime, timezone
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
