from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    BOQ_STATUSES,
    BUDGET_STATUSES,
    CHANGE_ORDER_IMPACT_TYPES,
    CHANGE_ORDER_STATUSES,
    CLAIM_STATUSES,
    CONTRACT_STATUSES,
    CONTRACT_TYPES,
    GRN_STATUSES,
    PAYMENT_METHODS,
    PAYMENT_STATUSES,
    PROCUREMENT_PRIORITIES,
    PROCUREMENT_STATUSES,
    PROJECT_STATUSES,
    PURCHASE_ORDER_STATUSES,
    SUBCONTRACT_STATUSES,
    SUPPLIER_INVOICE_STATUSES,
)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = "planning"
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal = Field(default=Decimal("0"), ge=0)
    client_name: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    client_name: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    status: str
    start_date: date | None
    end_date: date | None
    budget: Decimal
    client_name: str | None
    location: str | None
    created_by: UUID


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class ContractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    contract_number: str = Field(min_length=1, max_length=50)
    contract_type: str = "main"
    title: str = Field(min_length=1, max_length=200)
    counterparty: str = Field(min_length=1, max_length=200)
    contract_value: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = "draft"
    signed_date: date | None = None
    completion_date: date | None = None

    @field_validator("contract_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in CONTRACT_TYPES:
            raise ValueError(f"contract_type must be one of {sorted(CONTRACT_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTRACT_STATUSES)}")
        return v


class ContractUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    counterparty: str | None = Field(default=None, min_length=1, max_length=200)
    contract_value: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    signed_date: date | None = None
    completion_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTRACT_STATUSES)}")
        return v


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    contract_number: str
    contract_type: str
    title: str
    counterparty: str
    contract_value: Decimal
    status: str
    signed_date: date | None
    completion_date: date | None
    created_by: UUID


# ---------------------------------------------------------------------------
# BOQ
# ---------------------------------------------------------------------------
class BOQCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: UUID
    version: int = 1


class BOQUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in BOQ_STATUSES:
            raise ValueError(f"status must be one of {sorted(BOQ_STATUSES)}")
        return v


class BOQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    version: int
    status: str
    created_by: UUID


class BOQItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_number: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class BOQItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    boq_id: UUID
    item_number: int
    description: str
    unit: str
    quantity: Decimal
    unit_rate: Decimal
    amount: Decimal


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
class BudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    version: int = 1


class BudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in BUDGET_STATUSES:
            raise ValueError(f"status must be one of {sorted(BUDGET_STATUSES)}")
        return v


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    version: int
    status: str
    total_amount: Decimal
    created_by: UUID


class BudgetLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boq_item_id: UUID | None = None
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class BudgetLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    budget_id: UUID
    boq_item_id: UUID | None
    description: str
    unit: str
    quantity: Decimal
    unit_rate: Decimal
    amount: Decimal


# ---------------------------------------------------------------------------
# Progress Claim
# ---------------------------------------------------------------------------
class ProgressClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: UUID
    claim_number: str = Field(min_length=1, max_length=50)
    claim_date: date
    period_start: date
    period_end: date

    @field_validator("claim_date", "period_start", "period_end", mode="before")
    @classmethod
    def parse_date(cls, v: date | str) -> date:
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class ProgressClaimUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CLAIM_STATUSES:
            raise ValueError(f"status must be one of {sorted(CLAIM_STATUSES)}")
        return v


class ProgressClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    claim_number: str
    claim_date: date
    period_start: date
    period_end: date
    status: str
    total_amount: Decimal
    created_by: UUID


class ProgressClaimLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boq_item_id: UUID
    description: str = Field(min_length=1, max_length=500)
    quantity_completed: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class ProgressClaimLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    claim_id: UUID
    boq_item_id: UUID
    description: str
    quantity_completed: Decimal
    amount: Decimal


# ---------------------------------------------------------------------------
# Change Order
# ---------------------------------------------------------------------------
class ChangeOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    contract_id: UUID
    change_order_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    impact_type: str = "cost"
    cost_impact: Decimal = Field(default=Decimal("0"), ge=0)
    time_impact_days: int = Field(default=0, ge=0)

    @field_validator("impact_type")
    @classmethod
    def validate_impact_type(cls, v: str) -> str:
        if v not in CHANGE_ORDER_IMPACT_TYPES:
            raise ValueError(f"impact_type must be one of {sorted(CHANGE_ORDER_IMPACT_TYPES)}")
        return v


class ChangeOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    impact_type: str | None = None
    cost_impact: Decimal | None = Field(default=None, ge=0)
    time_impact_days: int | None = Field(default=None, ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CHANGE_ORDER_STATUSES:
            raise ValueError(f"status must be one of {sorted(CHANGE_ORDER_STATUSES)}")
        return v

    @field_validator("impact_type")
    @classmethod
    def validate_impact_type(cls, v: str | None) -> str | None:
        if v is not None and v not in CHANGE_ORDER_IMPACT_TYPES:
            raise ValueError(f"impact_type must be one of {sorted(CHANGE_ORDER_IMPACT_TYPES)}")
        return v


class ChangeOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    contract_id: UUID
    change_order_number: str
    title: str
    description: str
    status: str
    impact_type: str
    cost_impact: Decimal
    time_impact_days: int
    requested_by: UUID
    approved_by: UUID | None
    approved_at: date | None


# ---------------------------------------------------------------------------
# Subcontract
# ---------------------------------------------------------------------------
class SubcontractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    contract_id: UUID
    subcontract_number: str = Field(min_length=1, max_length=50)
    subcontractor_name: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=5000)
    value: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = "draft"
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in SUBCONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(SUBCONTRACT_STATUSES)}")
        return v


class SubcontractUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subcontractor_name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: str | None = Field(default=None, max_length=5000)
    value: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in SUBCONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(SUBCONTRACT_STATUSES)}")
        return v


class SubcontractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    contract_id: UUID
    subcontract_number: str
    subcontractor_name: str
    scope: str
    value: Decimal
    status: str
    start_date: date | None
    end_date: date | None
    created_by: UUID


# ---------------------------------------------------------------------------
# Site Warehouse
# ---------------------------------------------------------------------------
class SiteWarehouseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    manager_id: UUID | None = None


class SiteWarehouseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    manager_id: UUID | None = None


class SiteWarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    code: str
    name: str
    location: str | None
    manager_id: UUID | None


# ---------------------------------------------------------------------------
# Procurement
# ---------------------------------------------------------------------------
class ProcurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    requisition_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: str = "medium"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PROCUREMENT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROCUREMENT_PRIORITIES)}")
        return v


class ProcurementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    priority: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROCUREMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROCUREMENT_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in PROCUREMENT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROCUREMENT_PRIORITIES)}")
        return v


class ProcurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    requisition_number: str
    title: str
    description: str | None
    requested_by: UUID
    status: str
    priority: str
    total_estimated: Decimal


class ProcurementLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    estimated_unit_price: Decimal = Field(ge=0)
    estimated_total: Decimal = Field(ge=0)


class ProcurementLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    procurement_id: UUID
    description: str
    unit: str
    quantity: Decimal
    estimated_unit_price: Decimal
    estimated_total: Decimal


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------
class PurchaseOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    procurement_id: UUID
    supplier_id: UUID
    po_number: str = Field(min_length=1, max_length=50)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    terms: str | None = Field(default=None, max_length=5000)
    delivery_date: date | None = None


class PurchaseOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    terms: str | None = Field(default=None, max_length=5000)
    delivery_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PURCHASE_ORDER_STATUSES:
            raise ValueError(f"status must be one of {sorted(PURCHASE_ORDER_STATUSES)}")
        return v


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    procurement_id: UUID
    supplier_id: UUID
    po_number: str
    status: str
    total_amount: Decimal
    currency: str
    terms: str | None
    delivery_date: date | None
    created_by: UUID


class PurchaseOrderLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    procurement_line_id: UUID
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)


class PurchaseOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    purchase_order_id: UUID
    procurement_line_id: UUID
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


# ---------------------------------------------------------------------------
# Goods Receipt
# ---------------------------------------------------------------------------
class GoodsReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchase_order_id: UUID
    grn_number: str = Field(min_length=1, max_length=50)
    received_date: date
    warehouse_id: UUID
    received_by: UUID
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("received_date", mode="before")
    @classmethod
    def parse_date(cls, v: date | str) -> date:
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class GoodsReceiptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in GRN_STATUSES:
            raise ValueError(f"status must be one of {sorted(GRN_STATUSES)}")
        return v


class GoodsReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    purchase_order_id: UUID
    grn_number: str
    status: str
    received_date: date
    warehouse_id: UUID
    received_by: UUID
    notes: str | None


class GoodsReceiptLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_line_id: UUID
    quantity_received: Decimal = Field(gt=0)
    quantity_accepted: Decimal = Field(ge=0)
    quantity_rejected: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = Field(default=None, max_length=5000)


class GoodsReceiptLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    goods_receipt_id: UUID
    po_line_id: UUID
    quantity_received: Decimal
    quantity_accepted: Decimal
    quantity_rejected: Decimal
    notes: str | None


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------
class SupplierInvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchase_order_id: UUID
    grn_id: UUID | None = None
    invoice_number: str = Field(min_length=1, max_length=50)
    supplier_invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: date
    due_date: date
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("invoice_date", "due_date", mode="before")
    @classmethod
    def parse_date(cls, v: date | str) -> date:
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class SupplierInvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in SUPPLIER_INVOICE_STATUSES:
            raise ValueError(f"status must be one of {sorted(SUPPLIER_INVOICE_STATUSES)}")
        return v


class SupplierInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    purchase_order_id: UUID
    grn_id: UUID | None
    invoice_number: str
    supplier_invoice_number: str
    status: str
    invoice_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    submitted_by: UUID
    approved_by: UUID | None
    approved_at: date | None


class SupplierInvoiceLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grn_line_id: UUID | None = None
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)


class SupplierInvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    supplier_invoice_id: UUID
    grn_line_id: UUID | None
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    tax_rate: Decimal
    tax_amount: Decimal


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_invoice_id: UUID
    payment_number: str = Field(min_length=1, max_length=50)
    payment_method: str = "bank_transfer"
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    payment_date: date
    reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("payment_date", mode="before")
    @classmethod
    def parse_date(cls, v: date | str) -> date:
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(PAYMENT_METHODS)}")
        return v


class PaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PAYMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PAYMENT_STATUSES)}")
        return v


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    supplier_invoice_id: UUID
    payment_number: str
    status: str
    payment_method: str
    amount: Decimal
    currency: str
    payment_date: date
    reference: str | None
    notes: str | None
    created_by: UUID
    approved_by: UUID | None
    approved_at: date | None
    processed_at: date | None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class PendingApprovals(BaseModel):
    change_orders: int
    progress_claims: int
    purchase_orders: int


class DashboardResponse(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    by_status: dict[str, int]
    total_budget: Decimal
    total_spent: Decimal
    budget_utilization_pct: Decimal
    pending_approvals: PendingApprovals