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
CLAIM_STATUSES = {"draft", "submitted", "approved", "paid"}
PROCUREMENT_STATUSES = {"draft", "pending_approval", "approved", "ordered", "received", "cancelled"}
PROCUREMENT_PRIORITIES = {"low", "medium", "high", "urgent"}


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


class Procurement(Base):
    __tablename__ = "construction_procurements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "requisition_number",
            name="uq_construction_procurement_tenant_number",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'ordered', 'received', 'cancelled')",
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
