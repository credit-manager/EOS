from pydantic import BaseModel


class NotificationPrefs(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    weekly_report: bool = True
    project_updates: bool = True
    approval_requests: bool = True
    budget_alerts: bool = True
    payment_notifications: bool = True


class AppearancePrefs(BaseModel):
    theme: str = "light"
    sidebar_collapsed: bool = False
    compact_mode: bool = False


class SecurityPrefs(BaseModel):
    two_factor_enabled: bool = False
    session_timeout_minutes: int = 480
    password_min_length: int = 12


class TenantSettingsUpdate(BaseModel):
    company_name: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    currency: str | None = None
    fiscal_year_start: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    notifications: NotificationPrefs | None = None
    appearance: AppearancePrefs | None = None
    security: SecurityPrefs | None = None


class TenantSettingsResponse(BaseModel):
    id: str
    tenant_id: str
    company_name: str
    timezone: str
    date_format: str
    currency: str
    fiscal_year_start: str
    tax_id: str
    address: str
    phone: str
    email: str
    website: str
    logo_url: str
    notifications: dict
    appearance: dict
    security: dict

    model_config = {"from_attributes": True}
