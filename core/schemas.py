"""
EOS API Schemas — Request/Response Pydantic models.
Provides input validation for all critical API endpoints.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
import re
from decimal import Decimal
from datetime import date


class _NameMixin:
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    account_type: str = Field(..., pattern=r"^(asset|liability|equity|revenue|expense)$")
    parent_id: Optional[str] = None
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    opening_balance: Decimal = Field(Decimal("0"), ge=Decimal("0"))

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", v):
            raise ValueError("code must contain only alphanumeric chars, dots, hyphens, underscores")
        return v

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, v):
        return v.upper() if v else v


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)


class JournalLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(..., min_length=1, max_length=100)
    debit: Decimal = Field(Decimal("0"), ge=Decimal("0"))
    credit: Decimal = Field(Decimal("0"), ge=Decimal("0"))
    description: Optional[str] = Field(None, max_length=200)
    cost_center_id: Optional[str] = Field(None, max_length=100)

    def model_post_init(self, __context):
        if self.debit == 0 and self.credit == 0:
            raise ValueError("debit or credit must be non-zero")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("a journal line cannot contain both debit and credit")


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_date: date
    entry_type: str = Field(..., pattern=r"^(standard|adjusting|closing|opening|reversing)$")
    reference: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    fiscal_year_id: Optional[str] = Field(None, max_length=100)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class TenantProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    industry_code: str = Field(..., pattern=r"^(construction|trading|retail|restaurant|services|manufacturing)$")
    plan_id: Optional[str] = Field(None, max_length=100)
    admin_email: str = Field(..., max_length=254)
    admin_password: str = Field(..., min_length=8, max_length=128)
    admin_name: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


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
    hire_date: Optional[date] = None
    salary: Optional[Decimal] = Field(None, ge=Decimal("0"))
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    name_ar: Optional[str] = Field(None, max_length=200)
    sku: Optional[str] = Field(None, max_length=50)
    barcode: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    cost_price: Decimal = Field(Decimal("0"), ge=Decimal("0"))
    quantity_on_hand: int = Field(0, ge=0)
    reorder_level: int = Field(0, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)


class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    tax_number: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=50)
    credit_limit: Decimal = Field(Decimal("0"), ge=Decimal("0"))
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    tax_number: Optional[str] = Field(None, max_length=50)
    payment_terms: Optional[str] = Field(None, max_length=50)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)


class PaginationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class FilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, max_length=50)
    sort_by: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[str] = Field("desc", pattern=r"^(asc|desc)$")
