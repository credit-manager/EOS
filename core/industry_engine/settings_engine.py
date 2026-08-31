"""
EOS Industry Engine — Industry Settings
Currency, fiscal year, tax, and industry-specific configuration.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaxSystem(str, Enum):
    VAT = "vat"
    GST = "gst"
    SALES_TAX = "sales_tax"
    EXEMPT = "exempt"


class FiscalYearStart(str, Enum):
    JANUARY = "01-01"
    APRIL = "04-01"
    JULY = "07-01"
    CUSTOM = "custom"


@dataclass
class CurrencyConfig:
    code: str
    name: str
    name_ar: str
    symbol: str
    decimal_places: int = 2
    thousand_separator: str = ","
    decimal_separator: str = "."


@dataclass
class TaxConfig:
    tax_system: TaxSystem
    default_rate: float = 15.0  # e.g. 15% VAT
    vat_account: str = "2300"
    wht_rate: float = 0.0
    tax_inclusive: bool = False
    tax_registration_required: bool = True


@dataclass
class FiscalYearConfig:
    start_month_day: str = "01-01"
    periods: int = 12
    allow_adjusting_entries: bool = True
    closing_required: bool = True


@dataclass
class IndustrySettings:
    """Complete settings for an industry."""
    industry: str
    # Currency
    base_currency: str = "SAR"
    currencies: List[CurrencyConfig] = field(default_factory=list)
    # Tax
    tax: TaxConfig = field(default_factory=lambda: TaxConfig(tax_system=TaxSystem.VAT))
    # Fiscal Year
    fiscal_year: FiscalYearConfig = field(default_factory=FiscalYearConfig)
    # Number formatting
    number_format: str = "#,##0.00"
    date_format: str = "DD/MM/YYYY"
    # Features
    features: Dict[str, bool] = field(default_factory=dict)
    # Defaults
    defaults: Dict[str, Any] = field(default_factory=dict)
    # UI preferences
    rtl_default: bool = True
    theme: str = "light"
    # Industry-specific settings
    industry_config: Dict[str, Any] = field(default_factory=dict)


class SettingsEngine:
    """
    Manages industry-specific settings.
    Each industry template defines its default settings.
    """

    def __init__(self):
        self._settings: Dict[str, IndustrySettings] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register default settings for industries."""
        # SAR currency
        sar = CurrencyConfig(code="SAR", name="Saudi Riyal", name_ar="ريال سعودي", symbol="ر.س")
        usd = CurrencyConfig(code="USD", name="US Dollar", name_ar="دولار أمريكي", symbol="$")
        eur = CurrencyConfig(code="EUR", name="Euro", name_ar="يورو", symbol="€")

        # Core settings (SAR-based)
        core = IndustrySettings(
            industry="core",
            base_currency="SAR",
            currencies=[sar, usd, eur],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            fiscal_year=FiscalYearConfig(start_month_day="01-01"),
            features={
                "multi_company": True,
                "multi_branch": True,
                "multi_currency": True,
                "cost_centers": True,
                "project_accounting": False,
                "inventory_valuation": True,
                "batch_tracking": False,
                "serial_tracking": False,
                "barcode": False,
                "lot_tracking": False,
            },
            rtl_default=True,
        )
        self._settings["core"] = core

        # Construction settings
        construction = IndustrySettings(
            industry="construction",
            base_currency="SAR",
            currencies=[sar, usd],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            features={
                "multi_company": True,
                "multi_branch": True,
                "multi_currency": True,
                "cost_centers": True,
                "project_accounting": True,
                "boq": True,
                "variations": True,
                "progress_certificates": True,
                "retention": True,
                "advance_payment": True,
                "subcontractors": True,
                "equipment_tracking": True,
                "site_diary": True,
                "inspections": True,
                "rfi": True,
                "submittals": True,
                "claims": True,
                "warranty": True,
            },
            industry_config={
                "progress_method": "percentage",  # or "milestone"
                "retention_rate": 10.0,
                "max_advance_payment": 20.0,
                "boq_numbering": "sequential",
                "equipment_depreciation_method": "straight_line",
                "site_diary_required": True,
                "daily_progress_photo": False,
            },
        )
        self._settings["construction"] = construction

        # Trading settings
        trading = IndustrySettings(
            industry="trading",
            base_currency="SAR",
            currencies=[sar, usd, eur],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            features={
                "multi_company": True,
                "multi_branch": True,
                "multi_currency": True,
                "cost_centers": True,
                "batch_tracking": True,
                "serial_tracking": True,
                "barcode": True,
                "price_lists": True,
                "discounts": True,
                "credit_limits": True,
                "routes": True,
                "sales_rep": True,
                "delivery_notes": True,
                "returns": True,
            },
            industry_config={
                "pricing_method": "price_list",  # or "cost_plus"
                "default_payment_terms": "net30",
                "allow_negative_stock": False,
                "auto_reorder": False,
                "batch_expiry_tracking": True,
            },
        )
        self._settings["trading"] = trading

        # Restaurant settings
        restaurant = IndustrySettings(
            industry="restaurant",
            base_currency="SAR",
            currencies=[sar, usd],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            features={
                "multi_company": True,
                "multi_branch": True,
                "pos": True,
                "menu_management": True,
                "recipe_management": True,
                "kitchen_display": True,
                "table_management": True,
                "reservation": True,
                "delivery": True,
                "takeaway": True,
                "loyalty": True,
                "gift_cards": True,
                "waste_tracking": True,
                "food_costing": True,
                "shift_management": True,
                "daily_closing": True,
            },
            industry_config={
                "kitchen_printing": True,
                "auto_kitchen_display": True,
                "table_layout": "grid",
                "service_charge": 10.0,
                "tip_enabled": True,
                "delivery_partners": [],
                "recipe_costing_method": "average",
            },
        )
        self._settings["restaurant"] = restaurant

        # Manufacturing settings
        manufacturing = IndustrySettings(
            industry="manufacturing",
            base_currency="SAR",
            currencies=[sar, usd],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            features={
                "multi_company": True,
                "multi_branch": True,
                "bom": True,
                "multi_level_bom": True,
                "routing": True,
                "work_centers": True,
                "production_orders": True,
                "mrp": True,
                "capacity_planning": True,
                "quality_control": True,
                "batch_tracking": True,
                "serial_tracking": True,
                "scrap_tracking": True,
                "maintenance": True,
                "production_costing": True,
            },
            industry_config={
                "production_method": "make_to_order",
                "default_lead_time_days": 7,
                "scrap_account": "5400",
                "wip_account": "1350",
                "finished_goods_account": "1360",
                "quality_check_on_receipt": True,
                "auto_close_production": True,
            },
        )
        self._settings["manufacturing"] = manufacturing

        # Services settings
        services = IndustrySettings(
            industry="services",
            base_currency="SAR",
            currencies=[sar, usd, eur],
            tax=TaxConfig(tax_system=TaxSystem.VAT, default_rate=15.0),
            features={
                "multi_company": True,
                "multi_branch": True,
                "projects": True,
                "timesheets": True,
                "billable_hours": True,
                "service_rates": True,
                "retainers": True,
                "expense_tracking": True,
                "invoicing": True,
                "profitability": True,
            },
            industry_config={
                "billing_method": "hourly",  # hourly, fixed, retainer
                "default_hourly_rate": 500.0,
                "time_entry_increment": 0.25,  # 15 minutes
                "expense_approval_required": True,
                "project_profitability_calc": "accrual",
            },
        )
        self._settings["services"] = services

    def register(self, settings: IndustrySettings):
        """Register industry settings."""
        self._settings[settings.industry] = settings

    def get(self, industry: str) -> Optional[IndustrySettings]:
        """Get settings for an industry."""
        return self._settings.get(industry)

    def get_setting(self, industry: str, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        settings = self._settings.get(industry)
        if not settings:
            settings = self._settings.get("core")
        if settings:
            return getattr(settings, key, default)
        return default

    def get_feature(self, industry: str, feature: str) -> bool:
        """Check if a feature is enabled for an industry."""
        settings = self._settings.get(industry)
        if not settings:
            settings = self._settings.get("core")
        if settings:
            return settings.features.get(feature, False)
        return False

    def get_currency(self, industry: str) -> CurrencyConfig:
        """Get base currency config for an industry."""
        settings = self._settings.get(industry) or self._settings.get("core")
        if settings:
            for c in settings.currencies:
                if c.code == settings.base_currency:
                    return c
        return CurrencyConfig(code="SAR", name="Saudi Riyal", name_ar="ريال سعودي", symbol="ر.س")

    def get_tax_config(self, industry: str) -> TaxConfig:
        """Get tax config for an industry."""
        settings = self._settings.get(industry) or self._settings.get("core")
        if settings:
            return settings.tax
        return TaxConfig(tax_system=TaxSystem.VAT)

    def get_industry_config(self, industry: str) -> Dict[str, Any]:
        """Get industry-specific configuration."""
        settings = self._settings.get(industry)
        if settings:
            return settings.industry_config
        return {}

    def update_industry_config(self, industry: str, updates: Dict[str, Any]):
        """Update industry-specific configuration."""
        settings = self._settings.get(industry)
        if settings:
            settings.industry_config.update(updates)

    def export_settings(self, industry: str) -> Dict[str, Any]:
        """Export settings for templates."""
        settings = self._settings.get(industry)
        if not settings:
            return {}
        return {
            "industry": settings.industry,
            "base_currency": settings.base_currency,
            "tax": {
                "system": settings.tax.tax_system.value,
                "default_rate": settings.tax.default_rate,
                "vat_account": settings.tax.vat_account,
                "wht_rate": settings.tax.wht_rate,
            },
            "fiscal_year": {
                "start": settings.fiscal_year.start_month_day,
                "periods": settings.fiscal_year.periods,
            },
            "features": settings.features,
            "rtl_default": settings.rtl_default,
            "industry_config": settings.industry_config,
        }
