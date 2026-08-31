"""
EOS Experience Engine — UX Foundation
RTL/LTR, Arabic/English, Dark/Light, Responsive, White-label, Notifications.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class TextDirection(str, Enum):
    RTL = "rtl"
    LTR = "ltr"


class Language(str, Enum):
    ARABIC = "ar"
    ENGLISH = "en"


@dataclass
class ThemeConfig:
    primary_color: str = "#1890ff"
    success_color: str = "#52c41a"
    warning_color: str = "#faad14"
    error_color: str = "#ff4d4f"
    info_color: str = "#1890ff"
    border_radius: int = 8
    font_family: str = "Inter, system-ui, sans-serif"
    font_family_ar: str = "IBM Plex Sans Arabic, Tajawal, sans-serif"
    sidebar_bg: str = "#0f172a"
    header_bg: str = "#ffffff"
    content_bg: str = "#f8fafc"
    card_bg: str = "#ffffff"


@dataclass
class WhiteLabelConfig:
    system_name: str = "EOS"
    system_name_ar: str = "إي أو إس"
    logo_url: str = ""
    favicon_url: str = ""
    login_bg: str = ""
    primary_color: str = ""
    show_powered_by: bool = True
    custom_domain: str = ""
    email_template: str = ""
    sms_template: str = ""


@dataclass
class NotificationConfig:
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    language: str = "ar"


@dataclass
class ResponsiveConfig:
    mobile_breakpoint: int = 768
    tablet_breakpoint: int = 1024
    desktop_breakpoint: int = 1200
    sidebar_collapsed_width: int = 72
    sidebar_expanded_width: int = 240
    header_height: int = 64
    content_padding_mobile: int = 16
    content_padding_desktop: int = 32


class UXFoundation:
    """
    UX foundation for the Experience Engine.
    Manages themes, localization, responsive design, and white-labeling.
    """

    def __init__(self):
        self._themes: Dict[str, ThemeConfig] = {}
        self._white_labels: Dict[str, WhiteLabelConfig] = {}
        self._notifications: Dict[str, NotificationConfig] = {}
        self._responsive = ResponsiveConfig()
        self._register_builtins()

    def _register_builtins(self):
        """Register default themes."""
        self._themes["default"] = ThemeConfig()
        self._themes["dark"] = ThemeConfig(
            primary_color="#177ddc",
            sidebar_bg="#001529",
            header_bg="#141414",
            content_bg="#1f1f1f",
            card_bg="#262626",
        )
        self._themes["construction"] = ThemeConfig(
            primary_color="#1890ff",
            sidebar_bg="#0f172a",
        )
        self._themes["trading"] = ThemeConfig(
            primary_color="#52c41a",
            sidebar_bg="#0f2922",
        )
        self._themes["restaurant"] = ThemeConfig(
            primary_color="#fa541c",
            sidebar_bg="#1a0f0a",
        )
        self._themes["manufacturing"] = ThemeConfig(
            primary_color="#722ed1",
            sidebar_bg="#1a0f2e",
        )

        self._white_labels["default"] = WhiteLabelConfig()
        self._notifications["default"] = NotificationConfig()

    def get_theme(self, industry: str = "default") -> ThemeConfig:
        """Get theme config for an industry."""
        return self._themes.get(industry, self._themes["default"])

    def set_theme(self, industry: str, theme: ThemeConfig):
        """Set theme for an industry."""
        self._themes[industry] = theme

    def get_white_label(self, tenant_id: str = "") -> WhiteLabelConfig:
        """Get white-label config."""
        return self._white_labels.get(tenant_id, self._white_labels["default"])

    def set_white_label(self, tenant_id: str, config: WhiteLabelConfig):
        """Set white-label config for a tenant."""
        self._white_labels[tenant_id] = config

    def get_responsive(self) -> ResponsiveConfig:
        """Get responsive config."""
        return self._responsive

    def get_direction(self, language: str = "ar") -> str:
        """Get text direction for language."""
        return TextDirection.RTL.value if language == "ar" else TextDirection.LTR.value

    def get_font_family(self, language: str = "ar") -> str:
        """Get font family for language."""
        theme = self.get_theme()
        return theme.font_family_ar if language == "ar" else theme.font_family

    def generate_css_variables(self, industry: str = "default", language: str = "ar") -> Dict[str, str]:
        """Generate CSS variables for theming."""
        theme = self.get_theme(industry)
        direction = self.get_direction(language)
        return {
            "--primary-color": theme.primary_color,
            "--success-color": theme.success_color,
            "--warning-color": theme.warning_color,
            "--error-color": theme.error_color,
            "--info-color": theme.info_color,
            "--border-radius": f"{theme.border_radius}px",
            "--font-family": self.get_font_family(language),
            "--sidebar-bg": theme.sidebar_bg,
            "--header-bg": theme.header_bg,
            "--content-bg": theme.content_bg,
            "--card-bg": theme.card_bg,
            "--direction": direction,
        }

    def get_notification_config(self, tenant_id: str = "") -> NotificationConfig:
        return self._notifications.get(tenant_id, self._notifications["default"])

    def format_number(self, value: float, language: str = "ar", format_str: str = "#,##0.00") -> str:
        """Format number based on language/locale."""
        if language == "ar":
            # Arabic number formatting
            formatted = f"{value:,.2f}"
            # Replace Western digits with Arabic-Indic digits
            arabic_digits = "٠١٢٣٤٥٦٧٨٩"
            for i, d in enumerate("0123456789"):
                formatted = formatted.replace(d, arabic_digits[i])
            return formatted
        return f"{value:,.2f}"

    def format_date(self, date_str: str, language: str = "ar") -> str:
        """Format date based on language."""
        # Simple formatting - in production would use proper date library
        if language == "ar":
            return date_str.replace("/", "/")  # Keep DD/MM/YYYY for Arabic
        return date_str

    def get_currency_symbol(self, currency: str = "SAR", language: str = "ar") -> str:
        """Get currency symbol."""
        symbols = {
            "SAR": "ر.س" if language == "ar" else "SAR",
            "USD": "$",
            "EUR": "€",
            "AED": "د.إ" if language == "ar" else "AED",
            "EGP": "ج.م" if language == "ar" else "EGP",
        }
        return symbols.get(currency, currency)


# ═══════════════════════════════════════════════════
# Composite Experience Engine
# ═══════════════════════════════════════════════════

from .dashboard_engine import DashboardEngine
from .navigation_engine import NavigationEngine
from .form_engine import FormEngine
from .list_engine import ListEngine
from .report_engine import ReportEngine


class ExperienceEngine:
    """
    Composite engine that combines all UX sub-engines.
    Single entry point for the Experience Layer.
    """

    def __init__(self):
        self.dashboard = DashboardEngine()
        self.navigation = NavigationEngine()
        self.forms = FormEngine()
        self.lists = ListEngine()
        self.reports = ReportEngine()
        self.ux = UXFoundation()

    def get_industry_experience(self, industry: str, user_role: str = "",
                                features: List[str] = None) -> Dict[str, Any]:
        """
        Get complete UX experience for an industry.
        Returns dashboard, navigation, theme, and responsive config.
        """
        return {
            "dashboard": self.dashboard.generate_dashboard_data(industry),
            "navigation": self.navigation.get_menu(industry, user_role, features or []),
            "quick_actions": self.navigation.get_quick_actions(industry),
            "theme": {
                "industry": industry,
                "css_variables": self.ux.generate_css_variables(industry),
                "direction": self.ux.get_direction(),
                "font_family": self.ux.get_font_family(),
            },
            "responsive": {
                "mobile_breakpoint": self.ux.get_responsive().mobile_breakpoint,
                "tablet_breakpoint": self.ux.get_responsive().tablet_breakpoint,
                "sidebar_collapsed_width": self.ux.get_responsive().sidebar_collapsed_width,
                "sidebar_expanded_width": self.ux.get_responsive().sidebar_expanded_width,
                "header_height": self.ux.get_responsive().header_height,
            },
            "reports": self.reports.get_report_list(industry=industry),
        }

    def get_industry_form(self, entity: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get form for an entity."""
        form = self.forms.get_for_entity(entity)
        if form:
            return self.forms.generate_form(form.code, data)
        return self.forms.generate_from_entity(entity, data)

    def get_industry_list(self, entity: str, user_id: str = "") -> Dict[str, Any]:
        """Get list config for an entity."""
        return self.lists.generate_list_config(entity, user_id)

    def get_industry_report(self, code: str) -> Dict[str, Any]:
        """Get report config."""
        return self.reports.generate_report_config(code)


# Global instance
experience_engine = ExperienceEngine()
