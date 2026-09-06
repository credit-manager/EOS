from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid
from sqlalchemy.types import JSON


class FoundationBase(DeclarativeBase):
    pass


JSONType = JSON().with_variant(JSONB(), "postgresql")


class SalesOrderModel(FoundationBase):
    __tablename__ = "eos_v2_sales_orders"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    lines: Mapped[list] = mapped_column(JSONType, nullable=False)


class PurchaseOrderModel(FoundationBase):
    __tablename__ = "eos_v2_purchase_orders"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    lines: Mapped[list] = mapped_column(JSONType, nullable=False)


class InventoryMovementModel(FoundationBase):
    __tablename__ = "eos_v2_inventory_movements"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    item_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)


class StockBalanceModel(FoundationBase):
    __tablename__ = "eos_v2_stock_balances"
    __table_args__ = (UniqueConstraint("tenant_id", "item_id", name="uq_eos_v2_stock_balance"),)
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    item_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)


class EmployeeModel(FoundationBase):
    __tablename__ = "eos_v2_employees"
    __table_args__ = (UniqueConstraint("tenant_id", "employee_number", name="uq_eos_v2_employee_number"),)
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    employee_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class ProjectModel(FoundationBase):
    __tablename__ = "eos_v2_projects"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
