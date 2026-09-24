"""Marketplace foundation schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class MarketplaceAppCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    app_type: str = Field(..., max_length=50)
    category: str = Field(..., max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    author: str = Field(..., min_length=1, max_length=200)
    version: str = Field(default="1.0.0", max_length=20)
    min_eos_version: str | None = Field(default=None, max_length=20)
    max_eos_version: str | None = Field(default=None, max_length=20)
    icon_url: str | None = Field(default=None, max_length=500)
    screenshot_urls: list[str] | None = None
    demo_url: str | None = Field(default=None, max_length=500)
    documentation_url: str | None = Field(default=None, max_length=500)
    source_code_url: str | None = Field(default=None, max_length=500)
    license_type: str = Field(default="proprietary", max_length=50)
    license_url: str | None = Field(default=None, max_length=500)
    pricing_model: str = Field(default="free", max_length=50)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    trial_days: int | None = Field(default=None, ge=0)
    tags: list[str] | None = None
    compatibility: dict | None = None
    config: dict | None = None


class MarketplaceAppResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    short_description: str | None = None
    app_type: str
    category: str
    subcategory: str | None = None
    author: str
    author_id: str | None = None
    version: str
    min_eos_version: str | None = None
    max_eos_version: str | None = None
    icon_url: str | None = None
    screenshot_urls: list[str] | None = None
    demo_url: str | None = None
    documentation_url: str | None = None
    source_code_url: str | None = None
    license_type: str
    license_url: str | None = None
    pricing_model: str
    price: float | None = None
    currency: str | None = None
    trial_days: int | None = None
    is_published: bool
    is_featured: bool
    is_verified: bool
    rating: float | None = None
    rating_count: int
    install_count: int
    download_count: int
    tags: list[str] | None = None
    compatibility: dict | None = None
    config: dict | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None

    class Config:
        from_attributes = True


class MarketplaceCategoryCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=50)
    parent_id: str | None = None
    sort_order: int = 0


class MarketplaceCategoryResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    icon: str | None = None
    parent_id: str | None = None
    sort_order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MarketplaceReviewCreate(BaseModel):
    app_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    review_text: str | None = None


class MarketplaceReviewResponse(BaseModel):
    id: str
    app_id: str
    user_id: str
    rating: int
    title: str | None = None
    review_text: str | None = None
    is_verified_purchase: bool
    is_helpful_count: int
    developer_response: str | None = None
    developer_response_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarketplaceInstallationResponse(BaseModel):
    id: str
    app_id: str
    tenant_id: str
    user_id: str
    version: str
    status: str
    config: dict | None = None
    license_key: str | None = None
    installed_at: datetime
    updated_at: datetime
    uninstalled_at: datetime | None = None

    class Config:
        from_attributes = True


class MarketplaceOrderCreate(BaseModel):
    app_id: str = Field(..., min_length=1)
    order_type: str = Field(..., max_length=50)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    payment_method: str | None = Field(default=None, max_length=50)


class MarketplaceOrderResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    app_id: str
    order_type: str
    amount: float
    currency: str
    status: str
    payment_method: str | None = None
    payment_id: str | None = None
    license_key: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class MarketplaceAuthorCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=200)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    is_organization: bool = False


class MarketplaceAuthorResponse(BaseModel):
    id: str
    user_id: str
    display_name: str
    bio: str | None = None
    avatar_url: str | None = None
    website_url: str | None = None
    github_url: str | None = None
    is_verified: bool
    is_organization: bool
    total_apps: int
    total_installs: int
    average_rating: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
