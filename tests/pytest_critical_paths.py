"""Focused pytest coverage for critical accounting and authorization paths."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from core.accounting_engine import AccountingEngine
from core.auth import require_permission, require_platform_owner
from core.security import FieldSecurity, InputValidator, mask_sensitive_data, redact_audit_values


class FakeResult:
    def __init__(self, rows=None, rowcount=1):
        self.rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def scalar(self):
        return self.rows[0][0] if self.rows else None

    def first(self):
        return self.rows[0] if self.rows else None


# The authorization factory is a FastAPI dependency.  Unit-test the generated
# callable with an explicit user through its dependency contract rather than
# passing a user as a positional argument (which bypasses FastAPI injection).
def _permission_check(module: str, action: str):
    dependency = require_permission(module, action)
    return dependency.__defaults__[0].dependency
