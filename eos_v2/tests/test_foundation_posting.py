from decimal import Decimal
from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.foundation.posting import purchase_confirmation_posting, sales_confirmation_posting
from eos_v2.application.foundation.services import FoundationService
from eos_v2.modules.purchasing import PurchaseOrderLine, PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrderLine, SalesOrderStatus


def test_confirmed_sales_generates_balanced_instruction():
    token = set_tenant_context(TenantContext(uuid4(), uuid4()))
    try:
        order = FoundationService.create_sales_order(uuid4(), "USD", (SalesOrderLine(uuid4(), Decimal("2"), Decimal("50")),))
        order = FoundationService.transition_sales_order(order, SalesOrderStatus.CONFIRMED)
        instruction = sales_confirmation_posting(order, uuid4(), uuid4())
        assert instruction.amount == Decimal("100")
        assert instruction.source_module == "sales.order"
        assert sum(x.debit for x in instruction.lines()) == sum(x.credit for x in instruction.lines())
    finally:
        reset_tenant_context(token)


def test_unconfirmed_purchase_cannot_post():
    token = set_tenant_context(TenantContext(uuid4(), uuid4()))
    try:
        order = FoundationService.create_purchase_order(uuid4(), "USD", (PurchaseOrderLine(uuid4(), Decimal("1"), Decimal("20")),))
        with pytest.raises(ValueError): purchase_confirmation_posting(order, uuid4(), uuid4())
        confirmed = FoundationService.transition_purchase_order(order, PurchaseOrderStatus.CONFIRMED)
        assert purchase_confirmation_posting(confirmed, uuid4(), uuid4()).amount == Decimal("20")
    finally:
        reset_tenant_context(token)
