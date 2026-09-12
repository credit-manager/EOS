from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base

PROJECT_STATUSES = {"planning", "active", "on_hold", "completed", "cancelled"}
CONTRACT_STATUSES = {"draft", "pending_approval", "active", "completed", "terminated"}
CONTRACT_TYPES = {"main", "subcontract", "supply"}
BOQ_STATUSES = {"draft", "submitted", "approved"}
BUDGET_STATUSES = {"draft", "approved", "baselined"}
CLAIM_STATUSES = {"draft", "submitted", "approved", "paid"}
CHANGE_ORDER_STATUSES = {"draft", "pending_approval", "approved", "rejected", "implemented"}
CHANGE_ORDER_IMPACT_TYPES = {"cost", "time", "both"}
SUBCONTRACT_STATUSES = {"draft", "pending_approval", "active", "completed", "terminated"}
PROCUREMENT_STATUSES = {
    "draft",
    "pending_approval",
    "approved",
    "ordered",
    "received",
    "invoiced",
    "paid",
    "cancelled",
}
PROCUREMENT_PRIORITIES = {"low", "medium", "high", "urgent"}
PURCHASE_ORDER_STATUSES = {"draft", "sent", "acknowledged", "partial_received", "received", "cancelled"}
GRN_STATUSES = {"draft", "partial", "completed", "cancelled"}
SUPPLIER_INVOICE_STATUSES = {"draft", "pending_approval", "approved", "paid", "rejected", "cancelled"}
PAYMENT_STATUSES = {"draft", "pending_approval", "approved", "processing", "completed", "failed", "cancelled"}
PAYMENT_METHODS = {"bank_transfer", "check", "cash", "card", "other"}


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "construction_projects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_construction_project_tenant_code"),
        CheckConstraint(
            "status IN ('planning', 'active', 'on_hold', 'completed', 'cancelled')",
            name="ck_construction_project_status",
        ),
        Index("ix_construction_project_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planning")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class Contract(Base):
    __tablename__ = "construction_contracts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contract_number", name="uq_construction_contract_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'active', 'completed', 'terminated')",
            name="ck_construction_contract_status",
        ),
        CheckConstraint(
            "contract_type IN ('main', 'subcontract', 'supply')",
            name="ck_construction_contract_type",
        ),
        Index("ix_construction_contract_project", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    contract_number: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False, default="main")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(200), nullable=False)
    contract_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# BOQ (Bill of Quantities)
# ---------------------------------------------------------------------------
class BOQ(Base):
    __tablename__ = "construction_boqs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contract_id", "version", name="uq_construction_boq_version"
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved')", name="ck_construction_boq_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# BOQ Item
# ---------------------------------------------------------------------------
class BOQItem(Base):
    __tablename__ = "construction_boq_items"
    __table_args__ = (Index("ix_construction_boq_item_boq", "boq_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    boq_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_boqs.id", ondelete="RESTRICT"), nullable=False
    )
    item_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
class Budget(Base):
    __tablename__ = "construction_budgets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "version", name="uq_construction_budget_version"),
        CheckConstraint(
            "status IN ('draft', 'approved', 'baselined')", name="ck_construction_budget_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Budget Line
# ---------------------------------------------------------------------------
class BudgetLine(Base):
    __tablename__ = "construction_budget_lines"
    __table_args__ = (Index("ix_construction_budget_line_budget", "budget_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    budget_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_budgets.id", ondelete="RESTRICT"), nullable=False
    )
    boq_item_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("construction_boq_items.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Progress Claim
# ---------------------------------------------------------------------------
class ProgressClaim(Base):
    __tablename__ = "construction_progress_claims"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "claim_number", name="uq_construction_claim_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'paid')",
            name="ck_construction_claim_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False)
    claim_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Progress Claim Line
# ---------------------------------------------------------------------------
class ProgressClaimLine(Base):
    __tablename__ = "construction_progress_claim_lines"
    __table_args__ = (Index("ix_construction_claim_line_claim", "claim_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_progress_claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    boq_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_boq_items.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity_completed: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Change Order
# ---------------------------------------------------------------------------
class ChangeOrder(Base):
    __tablename__ = "construction_change_orders"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "change_order_number", name="uq_construction_change_order_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'rejected', 'implemented')",
            name="ck_construction_change_order_status",
        ),
        CheckConstraint(
            "impact_type IN ('cost', 'time', 'both')",
            name="ck_construction_change_order_impact",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    change_order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    impact_type: Mapped[str] = mapped_column(String(20), nullable=False, default="cost")
    cost_impact: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    time_impact_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Subcontract
# ---------------------------------------------------------------------------
class Subcontract(Base):
    __tablename__ = "construction_subcontracts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "subcontract_number", name="uq_construction_subcontract_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'active', 'completed', 'terminated')",
            name="ck_construction_subcontract_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    contract_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    subcontract_number: Mapped[str] = mapped_column(String(50), nullable=False)
    subcontractor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Site Warehouse
# ---------------------------------------------------------------------------
class SiteWarehouse(Base):
    __tablename__ = "construction_site_warehouses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_construction_warehouse_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Procurement (Requisition -> PO -> GRN -> Invoice -> Payment workflow)
# ---------------------------------------------------------------------------
class Procurement(Base):
    __tablename__ = "construction_procurements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "requisition_number",
            name="uq_construction_procurement_tenant_number",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'ordered', 'received', 'invoiced', 'paid', 'cancelled')",
            name="ck_construction_procurement_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_construction_procurement_priority",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="RESTRICT"), nullable=False
    )
    requisition_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    total_estimated: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Procurement Line
# ---------------------------------------------------------------------------
class ProcurementLine(Base):
    __tablename__ = "construction_procurement_lines"
    __table_args__ = (
        Index("ix_construction_procurement_line_parent", "procurement_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procurement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_procurements.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Purchase Order (linked to approved Procurement/Requisition)
# ---------------------------------------------------------------------------
class PurchaseOrder(Base):
    __tablename__ = "construction_purchase_orders"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "po_number", name="uq_construction_po_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'sent', 'acknowledged', 'partial_received', 'received', 'cancelled')",
            name="ck_construction_po_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procurement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_procurements.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Purchase Order Line
# ---------------------------------------------------------------------------
class PurchaseOrderLine(Base):
    __tablename__ = "construction_purchase_order_lines"
    __table_args__ = (Index("ix_construction_po_line_parent", "purchase_order_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_purchase_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    procurement_line_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_procurement_lines.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Goods Receipt Note (GRN)
# ---------------------------------------------------------------------------
class GoodsReceipt(Base):
    __tablename__ = "construction_goods_receipts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "grn_number", name="uq_construction_grn_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'partial', 'completed', 'cancelled')",
            name="ck_construction_grn_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    grn_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_site_warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    received_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Goods Receipt Line
# ---------------------------------------------------------------------------
class GoodsReceiptLine(Base):
    __tablename__ = "construction_goods_receipt_lines"
    __table_args__ = (Index("ix_construction_grn_line_parent", "goods_receipt_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goods_receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_goods_receipts.id", ondelete="RESTRICT"), nullable=False
    )
    po_line_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_purchase_order_lines.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------
class SupplierInvoice(Base):
    __tablename__ = "construction_supplier_invoices"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "invoice_number", name="uq_construction_invoice_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'paid', 'rejected', 'cancelled')",
            name="ck_construction_invoice_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    grn_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("construction_goods_receipts.id", ondelete="SET NULL"), nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    submitted_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Supplier Invoice Line
# ---------------------------------------------------------------------------
class SupplierInvoiceLine(Base):
    __tablename__ = "construction_supplier_invoice_lines"
    __table_args__ = (Index("ix_construction_invoice_line_parent", "supplier_invoice_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_supplier_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    grn_line_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("construction_goods_receipt_lines.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Project Financial Accounts
# ---------------------------------------------------------------------------
class ProjectFinancialAccounts(Base):
    """Account IDs for a construction project's financial accounts.

    These are configured per project/tenant during project setup.
    Each tenant/project combination has exactly one configuration.
    """

    __tablename__ = "construction_project_financial_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "project_id", name="uq_project_financial_accounts_tenant_project"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cash_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    accounts_receivable_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    accounts_payable_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    inventory_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    grni_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    materials_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    construction_revenue_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    labor_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    equipment_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    subcontractor_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    overhead_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    wip_account_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class Payment(Base):
    __tablename__ = "construction_payments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "payment_number", name="uq_construction_payment_tenant_number"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_construction_payment_status",
        ),
        CheckConstraint(
            "payment_method IN ('bank_transfer', 'check', 'cash', 'card', 'other')",
            name="ck_construction_payment_method",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("construction_supplier_invoices.id", ondelete="RESTRICT"), nullable=False
    )
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, default="bank_transfer")
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )