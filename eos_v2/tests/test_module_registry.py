from decimal import Decimal
from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.accounting.module_posting import PostingInstruction
from eos_v2.application.foundation.tenant_service import require_current_tenant
from eos_v2.modules.foundation.registry import FOUNDATION_MODULES


def test_foundation_registry_contains_all_core_modules() -> None:
    assert {item.key for item in FOUNDATION_MODULES.descriptors} == {
        "sales", "purchasing", "inventory", "hr", "projects"
    }
    assert FOUNDATION_MODULES.get("sales").version == "1.0.0"
    with pytest.raises(KeyError):
        FOUNDATION_MODULES.get("unknown")


def test_operational_posting_is_balanced_and_tenant_bound() -> None:
    tenant = uuid4()
    token = set_tenant_context(TenantContext(tenant))
    try:
        instruction = PostingInstruction(uuid4(), uuid4(), Decimal("125.00"), "sales", uuid4())
        debit, credit = instruction.lines()
        assert debit.debit == credit.credit == Decimal("125.00")
        instruction.validate_tenant_context(tenant)
        with pytest.raises(PermissionError):
            instruction.validate_tenant_context(uuid4())
    finally:
        reset_tenant_context(token)


def test_tenant_guard_fails_closed() -> None:
    class Resource:
        tenant_id = uuid4()

    token = set_tenant_context(TenantContext(uuid4()))
    try:
        with pytest.raises(PermissionError):
            require_current_tenant(Resource())
    finally:
        reset_tenant_context(token)
