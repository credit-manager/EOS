from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import hashlib
import json


def to_storage(value: Any) -> Any:
    """Convert domain values into deterministic JSON-compatible values."""
    if isinstance(value, UUID):
        return {"__eos_type__": "uuid", "value": str(value)}
    if isinstance(value, datetime):
        return {"__eos_type__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__eos_type__": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__eos_type__": "decimal", "value": str(value)}
    if isinstance(value, dict):
        return {str(key): to_storage(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_storage(item) for item in value]
    return value


def from_storage(value: Any) -> Any:
    if isinstance(value, dict):
        marker = value.get("__eos_type__")
        if marker == "uuid":
            return UUID(value["value"])
        if marker == "datetime":
            return datetime.fromisoformat(value["value"])
        if marker == "date":
            return date.fromisoformat(value["value"])
        if marker == "decimal":
            return Decimal(value["value"])
        return {key: from_storage(item) for key, item in value.items()}
    if isinstance(value, list):
        return [from_storage(item) for item in value]
    return value


def canonical_value(value: Any) -> str:
    """Return a fixed-width collision-resistant key for database uniqueness indexes."""
    payload = json.dumps(to_storage(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
