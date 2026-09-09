from decimal import Decimal
from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.foundation.services import FoundationService
from eos_v2.modules.purchasing import PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrderLine, SalesOrderStatus


def test_sales_lifecycle_is_forward_only():
    token = set_tenant_context(TenantContext(uuid4(), uuid4()))
    try:
        order = FoundationService.create_sales_order(uuid4(), "usd", (SalesOrderLine(uuid4(), Decimal("2"), Decimal("10")),))
        confirmed = FoundationService.transition_sales_order(order, SalesOrderStatus.CONFIRMED)
        assert confirmed.status is SalesOrderStatus.CONFIRMED
        with pytest.raises(ValueError):
            FoundationService.transition_sales_order(confirmed, SalesOrderStatus.DRAFT)
    finally:
        reset_tenant_context(token)


def test_inventory_cannot_go_negative_and_receipts_increase_stock():
    token = set_tenant_context(TenantContext(uuid4(), uuid4()))
    try:
        item = uuid4()
        with pytest.raises(ValueError, match="Insufficient stock"):
            FoundationService.apply_inventory_movement(item, Decimal("-1"), "issue", None)
        _, updated = FoundationService.apply_inventory_movement(item, Decimal("5"), "receipt", None)
        assert updated.quantity == Decimal("5")
    finally:
        reset_tenant_context(token)


def test_purchase_status_enum_is_stable():
    assert PurchaseOrderStatus.DRAFT.value == "draft"
    assert PurchaseOrderStatus.CONFIRMED.value == "confirmed"
