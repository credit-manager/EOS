"""
EOS API Schemas — Request/Response Pydantic models.
Provides input validation for all critical API endpoints.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
import re


class _NameMixin:
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)


# ═══════════════════════════════════════════════
# ACCOUNTING
# ═══════════════════════════════════════════════

class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    account_type: str = Field(..., pattern=r"^(asset|liability|equity|revenue|expense)$")
    parent_id: Optional[str] = None
    currency_code: Optional[str] = Field(None, max_length=3)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not re.match(r"^[A-Za-z0-9._-]+$", v):
            raise ValueError("code must contain only alphanumeric chars, dots, hyphens, underscores")
        return v


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    entry_date: Optional[str] = None
    lines: Optional[List[dict]] = None


class JournalLineAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str
    debit: float = Field(0, ge=0)
    credit: float = Field(0, ge=0)
    description: Optional[str] = Field(None, max_length=200)


# ═══════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name_ar: Optional[str] = Field(None, max_length=100)
    last_name_ar: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=200)
    company_code: Optional[str] = Field(None, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=10, max_length=500)


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(..., min_length=10, max_length=500)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=10, max_length=500)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


# ═══════════════════════════════════════════════
# WORKFLOW
# ═══════════════════════════════════════════════

class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=50)
    name_en: str = Field(..., min_length=1, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    entity_code: Optional[str] = Field(None, max_length=100)
    sla_hours: Optional[int] = Field(None, ge=1)


class WorkflowTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., pattern=r"^(approve|reject|return|escalate|cancel)$")
    comment: Optional[str] = Field(None, max_length=1000)


# ═══════════════════════════════════════════════
# COMPANY / ERP
# ═══════════════════════════════════════════════

class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    currency_code: Optional[str] = Field(None, max_length=3)
    tax_number: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=50)


# ═══════════════════════════════════════════════
# TENANT / COMPANY
# ═══════════════════════════════════════════════

class TenantProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    industry_code: str = Field(..., pattern=r"^(construction|trading|retail|restaurant|services|manufacturing)$")
    plan_id: Optional[str] = None
    admin_email: str = Field(..., max_length=254)
    admin_password: str = Field(..., min_length=8, max_length=128)
    admin_name: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=3)


# ═══════════════════════════════════════════════
# HR
# ═══════════════════════════════════════════════

class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name_ar: Optional[str] = Field(None, max_length=100)
    last_name_ar: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    hire_date: Optional[str] = None
    salary: Optional[float] = Field(None, ge=0)
    currency_code: Optional[str] = Field(None, max_length=3)


# ═══════════════════════════════════════════════
# INVENTORY / PRODUCTS
# ═══════════════════════════════════════════════

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    sku: Optional[str] = Field(None, max_length=50)
    barcode: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    unit_price: float = Field(..., ge=0)
    cost_price: float = Field(0, ge=0)
    quantity_on_hand: int = Field(0, ge=0)
    reorder_level: int = Field(0, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    currency_code: Optional[str] = Field(None, max_length=3)


# ═══════════════════════════════════════════════
# SALES
# ═══════════════════════════════════════════════

class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    tax_number: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=50)
    credit_limit: float = Field(0, ge=0)
    currency_code: Optional[str] = Field(None, max_length=3)


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    tax_number: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=50)
    currency_code: Optional[str] = Field(None, max_length=3)


# ═══════════════════════════════════════════════
# COMMON
# ═══════════════════════════════════════════════

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


# ═══════════════════════════════════════════════
# BILLING
# ═══════════════════════════════════════════════

class BillingCycleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(..., min_length=1)
    plan_id: str = Field(..., min_length=1)
    billing_period_start: Optional[str] = None
    billing_period_end: Optional[str] = None


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(..., min_length=1)
    customer_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[str] = None


# ═══════════════════════════════════════════════
# BLOCKCHAIN
# ═══════════════════════════════════════════════

class BlockchainNodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_name: str = Field(..., min_length=1, max_length=100)
    consensus: Optional[str] = Field(None, pattern=r"^(raft|pbft|raft-i_cfault|raft-c faulty)$")


class SmartContractDeploy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_name: str = Field(..., min_length=1, max_length=100)
    contract_code: str = Field(..., min_length=1)
    version: Optional[str] = Field(None, max_length=20)


# ═══════════════════════════════════════════════
# BUILDER
# ═══════════════════════════════════════════════

class BuilderProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    project_type: Optional[str] = Field(None, max_length=50)


# ═══════════════════════════════════════════════
# COMPLIANCE
# ═══════════════════════════════════════════════

class ComplianceCheckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_type: str = Field(..., min_length=1, max_length=100)
    entity_id: str = Field(..., min_length=1)
    check_type: str = Field(..., min_length=1, max_length=100)


# ═══════════════════════════════════════════════
# FINANCE
# ═══════════════════════════════════════════════

class BudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    total_amount: float = Field(..., ge=0)


# ═══════════════════════════════════════════════
# E-SIGNATURE
# ═══════════════════════════════════════════════

class SignatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(..., min_length=1)
    signer_email: str = Field(..., max_length=254)
    signer_name: Optional[str] = Field(None, max_length=200)

    @field_validator("signer_email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()


# ═══════════════════════════════════════════════
# CONTROL PLANE
# ═══════════════════════════════════════════════

class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    max_users: int = Field(..., ge=1)
    max_companies: int = Field(..., ge=1)
    monthly_price: float = Field(..., ge=0)
    annual_price: float = Field(0, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    features: Optional[str] = None


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern=r"^(active|suspended|cancelled)$")
    plan_id: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_companies: Optional[int] = Field(None, ge=1)


class FilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, max_length=50)
    sort_by: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[str] = Field("desc", pattern=r"^(asc|desc)$")
