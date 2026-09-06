from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.modules.hr import Employee
from eos_v2.modules.inventory import InventoryMovement, StockBalance
from eos_v2.modules.projects import Project
from eos_v2.modules.purchasing import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrder, SalesOrderLine, SalesOrderStatus


class FoundationService:
    """Application boundary for foundation aggregates; repositories remain infrastructure concerns."""

    @staticmethod
    def tenant() -> UUID:
        return get_tenant_context().tenant_id

    @staticmethod
    def create_sales_order(customer_id: UUID, currency: str, lines: tuple[SalesOrderLine, ...]) -> SalesOrder:
        return SalesOrder(tenant_id=FoundationService.tenant(), customer_id=customer_id, currency=currency.upper(), lines=lines)

    @staticmethod
    def transition_sales_order(order: SalesOrder, status: SalesOrderStatus) -> SalesOrder:
        if order.tenant_id != FoundationService.tenant():
            raise PermissionError("Cross-tenant operation denied")
        allowed = {SalesOrderStatus.DRAFT: {SalesOrderStatus.CONFIRMED, SalesOrderStatus.CANCELLED}, SalesOrderStatus.CONFIRMED: {SalesOrderStatus.CANCELLED}, SalesOrderStatus.CANCELLED: set()}
        if status not in allowed[order.status]:
            raise ValueError(f"Invalid sales order transition: {order.status.value} -> {status.value}")
        return replace(order, status=status)

    @staticmethod
    def create_purchase_order(supplier_id: UUID, currency: str, lines: tuple[PurchaseOrderLine, ...]) -> PurchaseOrder:
        return PurchaseOrder(tenant_id=FoundationService.tenant(), supplier_id=supplier_id, currency=currency.upper(), lines=lines)

    @staticmethod
    def transition_purchase_order(order: PurchaseOrder, status: PurchaseOrderStatus) -> PurchaseOrder:
        if order.tenant_id != FoundationService.tenant():
            raise PermissionError("Cross-tenant operation denied")
        allowed = {PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.CANCELLED}, PurchaseOrderStatus.CONFIRMED: {PurchaseOrderStatus.CANCELLED}, PurchaseOrderStatus.CANCELLED: set()}
        if status not in allowed[order.status]:
            raise ValueError(f"Invalid purchase order transition: {order.status.value} -> {status.value}")
        return replace(order, status=status)

    @staticmethod
    def create_employee(employee_number: str, name: str, hire_date: date) -> Employee:
        return Employee(tenant_id=FoundationService.tenant(), employee_number=employee_number, name=name, hire_date=hire_date)

    @staticmethod
    def create_project(code: str, name: str, start_date: date, end_date: date | None = None) -> Project:
        return Project(tenant_id=FoundationService.tenant(), code=code, name=name, start_date=start_date, end_date=end_date)

    @staticmethod
    def apply_inventory_movement(item_id: UUID, quantity: Decimal, source: str, balance: StockBalance | None) -> tuple[InventoryMovement, StockBalance]:
        movement = InventoryMovement(tenant_id=FoundationService.tenant(), item_id=item_id, quantity=quantity, source=source)
        current = balance or StockBalance(tenant_id=FoundationService.tenant(), item_id=item_id, quantity=Decimal("0"))
        if current.tenant_id != FoundationService.tenant():
            raise PermissionError("Cross-tenant inventory operation denied")
        new_quantity = current.quantity + quantity
        if new_quantity < 0:
            raise ValueError("Insufficient stock")
        return movement, replace(current, quantity=new_quantity)
