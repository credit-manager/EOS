from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.infrastructure.db.foundation_models import EmployeeModel, InventoryMovementModel, ProjectModel, PurchaseOrderModel, SalesOrderModel, StockBalanceModel
from eos_v2.modules.hr import Employee
from eos_v2.modules.projects import Project, ProjectStatus
from eos_v2.modules.purchasing import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrder, SalesOrderLine, SalesOrderStatus
from eos_v2.modules.inventory import InventoryMovement, StockBalance


def _tenant() -> UUID:
    return get_tenant_context().tenant_id


class FoundationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_sales(self, order: SalesOrder) -> None:
        self._check(order.tenant_id)
        self.session.merge(SalesOrderModel(id=order.id, tenant_id=order.tenant_id, customer_id=order.customer_id, currency=order.currency, status=order.status.value, lines=[{"item_id": str(l.item_id), "quantity": str(l.quantity), "unit_price": str(l.unit_price)} for l in order.lines]))

    def get_sales(self, order_id: UUID) -> SalesOrder:
        row = self.session.scalar(select(SalesOrderModel).where(SalesOrderModel.id == order_id, SalesOrderModel.tenant_id == _tenant()))
        if row is None: raise KeyError("Sales order not found")
        return SalesOrder(tenant_id=row.tenant_id, customer_id=row.customer_id, currency=row.currency, status=SalesOrderStatus(row.status), lines=tuple(SalesOrderLine(UUID(x["item_id"]), Decimal(x["quantity"]), Decimal(x["unit_price"])) for x in row.lines), id=row.id)

    def save_purchase(self, order: PurchaseOrder) -> None:
        self._check(order.tenant_id)
        self.session.merge(PurchaseOrderModel(id=order.id, tenant_id=order.tenant_id, supplier_id=order.supplier_id, currency=order.currency, status=order.status.value, lines=[{"item_id": str(l.item_id), "quantity": str(l.quantity), "unit_cost": str(l.unit_cost)} for l in order.lines]))

    def get_purchase(self, order_id: UUID) -> PurchaseOrder:
        row = self.session.scalar(select(PurchaseOrderModel).where(PurchaseOrderModel.id == order_id, PurchaseOrderModel.tenant_id == _tenant()))
        if row is None: raise KeyError("Purchase order not found")
        return PurchaseOrder(tenant_id=row.tenant_id, supplier_id=row.supplier_id, currency=row.currency, status=PurchaseOrderStatus(row.status), lines=tuple(PurchaseOrderLine(UUID(x["item_id"]), Decimal(x["quantity"]), Decimal(x["unit_cost"])) for x in row.lines), id=row.id)

    def save_employee(self, employee: Employee) -> None:
        self._check(employee.tenant_id)
        self.session.merge(EmployeeModel(id=employee.id, tenant_id=employee.tenant_id, employee_number=employee.employee_number, name=employee.name, hire_date=employee.hire_date, active=employee.active))

    def get_employee(self, employee_id: UUID) -> Employee:
        row = self.session.scalar(select(EmployeeModel).where(EmployeeModel.id == employee_id, EmployeeModel.tenant_id == _tenant()))
        if row is None: raise KeyError("Employee not found")
        return Employee(tenant_id=row.tenant_id, employee_number=row.employee_number, name=row.name, hire_date=row.hire_date, active=row.active, id=row.id)

    def save_project(self, project: Project) -> None:
        self._check(project.tenant_id)
        self.session.merge(ProjectModel(id=project.id, tenant_id=project.tenant_id, code=project.code, name=project.name, status=project.status.value, start_date=project.start_date, end_date=project.end_date))

    def get_project(self, project_id: UUID) -> Project:
        row = self.session.scalar(select(ProjectModel).where(ProjectModel.id == project_id, ProjectModel.tenant_id == _tenant()))
        if row is None: raise KeyError("Project not found")
        return Project(tenant_id=row.tenant_id, code=row.code, name=row.name, start_date=row.start_date, end_date=row.end_date, status=ProjectStatus(row.status), id=row.id)

    def save_inventory(self, movement: InventoryMovement, balance: StockBalance) -> None:
        self._check(movement.tenant_id)
        self._check(balance.tenant_id)
        row = self.session.scalar(select(StockBalanceModel).where(StockBalanceModel.item_id == balance.item_id, StockBalanceModel.tenant_id == _tenant()))
        if row is None:
            self.session.add(StockBalanceModel(id=balance.id, tenant_id=balance.tenant_id, item_id=balance.item_id, quantity=balance.quantity))
        else:
            row.quantity = balance.quantity
        self.session.add(InventoryMovementModel(id=movement.id, tenant_id=movement.tenant_id, item_id=movement.item_id, quantity=movement.quantity, source=movement.reference_type))

    def apply_inventory_movement(self, movement: InventoryMovement) -> StockBalance:
        """Persist a movement and update its tenant/item balance atomically on PostgreSQL."""
        self._check(movement.tenant_id)
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            statement = (
                pg_insert(StockBalanceModel)
                .values(
                    id=UUID(int=0),
                    tenant_id=movement.tenant_id,
                    item_id=movement.item_id,
                    quantity=movement.quantity,
                )
                .on_conflict_do_update(
                    constraint="uq_eos_v2_stock_balance",
                    set_={"quantity": StockBalanceModel.quantity + movement.quantity},
                    where=(StockBalanceModel.quantity + movement.quantity >= 0),
                )
            )
            self.session.execute(statement)
        else:
            row = self.session.scalar(
                select(StockBalanceModel)
                .where(StockBalanceModel.item_id == movement.item_id, StockBalanceModel.tenant_id == _tenant())
                .with_for_update()
            )
            if row is None:
                if movement.quantity < 0:
                    raise ValueError("Insufficient stock")
                self.session.add(StockBalanceModel(id=UUID(int=0), tenant_id=movement.tenant_id, item_id=movement.item_id, quantity=movement.quantity))
            else:
                new_quantity = Decimal(row.quantity) + movement.quantity
                if new_quantity < 0:
                    raise ValueError("Insufficient stock")
                row.quantity = new_quantity

        self.session.add(
            InventoryMovementModel(
                id=movement.id,
                tenant_id=movement.tenant_id,
                item_id=movement.item_id,
                quantity=movement.quantity,
                source=movement.reference_type,
            )
        )
        self.session.flush()
        row = self.session.scalar(
            select(StockBalanceModel).where(
                StockBalanceModel.item_id == movement.item_id,
                StockBalanceModel.tenant_id == _tenant(),
            )
        )
        if row is None:
            raise RuntimeError("Inventory balance update did not produce a balance")
        return StockBalance(tenant_id=row.tenant_id, item_id=row.item_id, quantity=Decimal(row.quantity), id=row.id)

    def get_stock(self, item_id: UUID) -> StockBalance:
        row = self.session.scalar(select(StockBalanceModel).where(StockBalanceModel.item_id == item_id, StockBalanceModel.tenant_id == _tenant()))
        if row is None: return StockBalance(tenant_id=_tenant(), item_id=item_id, quantity=Decimal("0"))
        return StockBalance(tenant_id=row.tenant_id, item_id=row.item_id, quantity=Decimal(row.quantity), id=row.id)

    @staticmethod
    def _check(tenant_id: UUID) -> None:
        if tenant_id != _tenant(): raise PermissionError("Cross-tenant operation denied")
