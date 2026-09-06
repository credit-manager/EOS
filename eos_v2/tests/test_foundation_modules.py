from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from eos_v2.modules.hr import Employee
from eos_v2.modules.inventory import InventoryMovement, StockBalance
from eos_v2.modules.projects import Project
from eos_v2.modules.purchasing import PurchaseOrder, PurchaseOrderLine
from eos_v2.modules.sales import SalesOrder, SalesOrderLine


def test_sales_order_total_and_validation() -> None:
    order = SalesOrder(uuid4(), uuid4(), "usd", (SalesOrderLine(uuid4(), Decimal("2"), Decimal("10")),))
    assert order.lines[0].total == Decimal("20")
    with pytest.raises(ValueError):
        SalesOrder(uuid4(), uuid4(), "USD", ())


def test_purchase_order_requires_positive_lines() -> None:
    with pytest.raises(ValueError):
        PurchaseOrder(uuid4(), uuid4(), "USD", (PurchaseOrderLine(uuid4(), Decimal("0"), Decimal("1")),))


def test_inventory_rejects_zero_movement_and_negative_balance() -> None:
    with pytest.raises(ValueError):
        InventoryMovement(uuid4(), uuid4(), Decimal("0"), "sale", uuid4())
    with pytest.raises(ValueError):
        StockBalance(uuid4(), uuid4(), Decimal("-1"))


def test_employee_and_project_dates() -> None:
    employee = Employee(uuid4(), "EMP-1", "Alice", date(2026, 1, 1))
    assert employee.active
    with pytest.raises(ValueError):
        Project(uuid4(), "P-1", "Build", date(2026, 5, 1), end_date=date(2026, 4, 1))
