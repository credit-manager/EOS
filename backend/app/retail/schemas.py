from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── Product ──

class ProductCreate(BaseModel):
    tenant_id: int
    sku: str
    name: str
    description: str | None = None
    category: str | None = None
    unit_price: int = 0
    cost_price: int = 0
    stock_quantity: int = 0
    min_stock: int = 0
    is_active: bool = True


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    unit_price: int | None = None
    cost_price: int | None = None
    stock_quantity: int | None = None
    min_stock: int | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    sku: str
    name: str
    description: str | None
    category: str | None
    unit_price: int
    cost_price: int
    stock_quantity: int
    min_stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── POS Transaction ──

class POSTransactionCreate(BaseModel):
    tenant_id: int
    transaction_number: str
    customer_name: str | None = None
    total_amount: int = 0
    tax_amount: int = 0
    payment_method: str
    status: str = "completed"


class POSTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    transaction_number: str
    customer_name: str | None
    total_amount: int
    tax_amount: int
    payment_method: str
    status: str
    created_at: datetime


class POSTransactionLineCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: int = 0
    total: int = 0


class POSTransactionLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    product_id: int
    quantity: int
    unit_price: int
    total: int


# ── Inventory Count ──

class InventoryCountCreate(BaseModel):
    tenant_id: int
    count_number: str
    counted_by: str | None = None
    notes: str | None = None


class InventoryCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    count_number: str
    status: str
    counted_by: str | None
    notes: str | None
    created_at: datetime
    completed_at: datetime | None


class InventoryCountLineCreate(BaseModel):
    product_id: int
    expected_qty: int = 0
    counted_qty: int = 0
    variance: int = 0


class InventoryCountLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    count_id: int
    product_id: int
    expected_qty: int
    counted_qty: int
    variance: int


# ── Loyalty Member ──

class LoyaltyMemberCreate(BaseModel):
    tenant_id: int
    member_number: str
    name: str
    email: str | None = None
    phone: str | None = None
    points: int = 0
    tier: str = "standard"
    is_active: bool = True


class LoyaltyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    member_number: str
    name: str
    email: str | None
    phone: str | None
    points: int
    tier: str
    is_active: bool
    created_at: datetime


class LoyaltyPointsAdd(BaseModel):
    points: int
