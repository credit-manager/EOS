"""
Saudi Arabia (KSA) Pack - reference implementation for Globalization Engine.

Provides Saudi Arabia-specific:
- Tax rules (VAT 15%, Zakat, withholding tax)
- E-invoice formatting per ZATCA (Fatoora) standards
- Statutory reports (VAT return, Zakat return, SAWTA)
- Fiscal calendar (Saudi fiscal year: January 1 - December 31)
- Numbering conventions
- Currency formatting (SAR)
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Country, CountryPack, Currency, TaxConfig

logger = logging.getLogger("2to-eos.globalization.ksa")


class KSAPackService:
    """
    Saudi Arabia Pack implementation.

    Reference implementation showing how a country pack should work:
    - Tax calculation with Saudi VAT rules (15% standard rate)
    - E-invoice generation in ZATCA Fatoora format
    - Statutory report generation (VAT, Zakat, SAWTA)
    - Saudi fiscal year (Jan 1 - Dec 31)
    - Arabic/English bilingual support
    """

    KSA_CODE = "SA"
    KSA_CURRENCY = "SAR"
    SAR_VAT_RATE = 15.0
    SAR_ZERO_RATE = 0.0
    ZAKAT_RATE = 2.5  # 2.5% zakat on net assets for Saudi entities

    # Saudi VAT exemptions (selected common categories)
    VAT_EXEMPT_CATEGORIES = [
        "financial_services",
        "residential_rental",
        "intra_community_supply",
        "exported_goods",
        "international_transports",
        "bare_land",
        "falconry",
    ]

    # Saudi fiscal year
    FISCAL_YEAR_START = 1  # January
    FISCAL_YEAR_END = 12   # December

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------------
    # Country & Pack Management
    # ---------------------------------------------------------------

    def ensure_ksa_country(self) -> Country:
        """Ensure Saudi Arabia country record exists"""
        country = self.db.scalar(
            select(Country).where(Country.code == self.KSA_CODE)
        )
        if country:
            return country

        country = Country(
            code=self.KSA_CODE,
            name="Saudi Arabia",
            native_name="المملكة العربية السعودية",
            currency_code=self.KSA_CURRENCY,
            currency_name="Saudi Riyal",
            currency_symbol="﷼",
            language_code="ar",
            language_name="Arabic",
            timezone="Asia/Riyadh",
            phone_code="+966",
            date_format="DD/MM/YYYY",
            number_format="#,##0.00",
        )
        self.db.add(country)
        self.db.commit()
        self.db.refresh(country)
        logger.info("Saudi Arabia country record created")
        return country

    def ensure_ksa_currency(self) -> Currency:
        """Ensure SAR currency record exists"""
        currency = self.db.scalar(
            select(Currency).where(Currency.code == self.KSA_CURRENCY)
        )
        if currency:
            return currency

        currency = Currency(
            code=self.KSA_CURRENCY,
            name="Saudi Riyal",
            symbol="﷼",
            decimal_places=2,
        )
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        logger.info("SAR currency record created")
        return currency

    def ensure_ksa_pack(self) -> CountryPack:
        """Ensure Saudi Arabia pack exists with full configuration"""
        pack = self.db.scalar(
            select(CountryPack).where(
                CountryPack.country_code == self.KSA_CODE,
                CountryPack.is_active.is_(True)
            )
        )
        if pack:
            return pack

        pack = CountryPack(
            country_code=self.KSA_CODE,
            pack_name="Saudi Arabia Pack",
            pack_version="1.0.0",
            pack_config={
                "country_code": self.KSA_CODE,
                "currency": self.KSA_CURRENCY,
                "language": "ar",
                "timezone": "Asia/Riyadh",
                "date_format": "DD/MM/YYYY",
                "number_format": "#,##0.00",
                "fiscal_year_start_month": self.FISCAL_YEAR_START,
                "fiscal_year_end_month": self.FISCAL_YEAR_END,
                "week_start_day": "Saturday",
            },
            tax_config={
                "vat_rate": self.SAR_VAT_RATE,
                "reduced_vat_rate": None,
                "zero_rated": self.SAR_ZERO_RATE,
                "exempt_categories": self.VAT_EXEMPT_CATEGORIES,
                "reduced_categories": [],
            },
            accounting_config={
                "currency": self.KSA_CURRENCY,
                "fiscal_year_start": self.FISCAL_YEAR_START,
                "fiscal_year_end": self.FISCAL_YEAR_END,
                "accounting_basis": "accrual",
                "zakat_applies": True,
                "zakat_rate": self.ZAKAT_RATE,
            },
            e_invoice_config={
                "standard": "ZATCA Fatoora (E-Invoice) standard",
                "version": "1.0",
                "integration": "ZATCA E-Invoice Platform (Fatoora)",
                "authorization_required": True,
                "invoice_types": [
                    "simplified", "nominal", "copy",
                    "debit_note", "credit_note",
                ],
                "required_fields": [
                    "invoice_number",
                    "invoice_date",
                    "seller_vat_number",
                    "buyer_vat_number",
                    "taxable_amount",
                    "vat_amount",
                    "total_amount",
                    "currency",
                ],
                "indicators": {
                    "billing_type": "direct",
                    "device_id": "ZATCA-registered POS/device ID",
                },
            },
            compliance_config={
                "statutory_reports": [
                    "VAT Return Quarterly (ZATCA)",
                    "Zakat Return Annual",
                    "Withholding Tax Return",
                ],
                "audit_trail_required": True,
                "invoice_retention_years": 10,
                "sawta_registration_required": True,
            },
            fiscal_calendar={
                "start_month": self.FISCAL_YEAR_START,
                "end_month": self.FISCAL_YEAR_END,
                "quarters": [
                    {"name": "Q1", "months": [1, 2, 3]},
                    {"name": "Q2", "months": [4, 5, 6]},
                    {"name": "Q3", "months": [7, 8, 9]},
                    {"name": "Q4", "months": [10, 11, 12]},
                ],
                "vat_returns": "Quarterly",
                "annual_return_due": "June 30",
            },
            statutory_reports={
                "vat_return_quarterly": {
                    "title": "إقرار ضريبة القيمة المضافة ربعي (زاتكا)",
                    "frequency": "Quarterly",
                    "due_days_after_period": 15,
                    "required_data": [
                        "total_sales",
                        "total_purchases",
                        "vat_collected",
                        "vat_paid",
                        "net_vat_due",
                    ],
                },
                "zakat_return_annual": {
                    "title": "إقرار الزكاة السنوي",
                    "frequency": "Annual",
                    "due_days_after_year_end": 60,
                    "required_data": [
                        "net_assets",
                        "zakat_base",
                        "zakat_due",
                    ],
                },
                "withholding_tax": {
                    "title": "ضريبة الدخل المخصوم",
                    "frequency": "Monthly",
                    "due_days_after_period": 15,
                    "required_data": [
                        "total_payments",
                        "tax_withheld",
                        "net_tax_due",
                    ],
                },
            },
            is_active=True,
        )
        self.db.add(pack)
        self.db.commit()
        self.db.refresh(pack)
        logger.info("Saudi Arabia Pack created")
        return pack

    # ---------------------------------------------------------------
    # Unified interface methods (for pack registry)
    # ---------------------------------------------------------------

    def ensure_country(self) -> Country:
        """Unified interface: ensure KSA country record."""
        return self.ensure_ksa_country()

    def ensure_currency(self) -> Currency:
        """Unified interface: ensure SAR currency record."""
        return self.ensure_ksa_currency()

    def ensure_pack(self) -> CountryPack:
        """Unified interface: ensure KSA pack record."""
        return self.ensure_ksa_pack()

    def ensure_tax_configs(self) -> list:
        """Unified interface: ensure KSA tax configs."""
        return self.ensure_ksa_tax_configs()

    def ensure_ksa_tax_configs(self) -> list[TaxConfig]:
        """Create Saudi Arabia VAT and Zakat tax configurations"""
        configs = []
        tax_definitions = [
            {
                "tax_type": "vat_standard",
                "tax_name": "ضريبة القيمة المضافة السعودية (15%)",
                "tax_rate": self.SAR_VAT_RATE,
                "effective_from": datetime(2019, 1, 1),
            },
            {
                "tax_type": "zakat",
                "tax_name": "زكاة الأعمال",
                "tax_rate": self.ZAKAT_RATE,
                "effective_from": datetime(2024, 1, 1),
            },
            {
                "tax_type": "withholding_tax",
                "tax_name": "ضريبة الدخل المخصوم من المدفوعات",
                "tax_rate": 5.0,
                "effective_from": datetime(2024, 1, 1),
            },
        ]

        for tax_def in tax_definitions:
            existing = self.db.scalar(
                select(TaxConfig).where(
                    TaxConfig.country_code == self.KSA_CODE,
                    TaxConfig.tax_type == tax_def["tax_type"],
                )
            )
            if existing:
                configs.append(existing)
                continue

            tax = TaxConfig(
                country_code=self.KSA_CODE,
                **tax_def,
            )
            self.db.add(tax)
            configs.append(tax)

        self.db.commit()
        for c in configs:
            self.db.refresh(c)
        logger.info("KSA tax configs created: %d", len(configs))
        return configs

    # ---------------------------------------------------------------
    # Full KSA Pack Initialization
    # ---------------------------------------------------------------

    def initialize_ksa_pack(self) -> dict:
        """Initialize the complete Saudi Arabia Pack (idempotent)"""
        result = {
            "country": None,
            "currency": None,
            "pack": None,
            "tax_configs": [],
            "status": "initialized",
        }

        result["country"] = self.ensure_ksa_country()
        result["currency"] = self.ensure_ksa_currency()
        result["pack"] = self.ensure_ksa_pack()
        result["tax_configs"] = self.ensure_ksa_tax_configs()

        logger.info("KSA Pack fully initialized: %s", result["pack"].pack_version)
        return result

    # ---------------------------------------------------------------
    # VAT Calculation (common interface)
    # ---------------------------------------------------------------

    def calculate_vat(
        self,
        taxable_amount: float,
        tax_category: str | None = None,
    ) -> dict:
        """Calculate VAT for a taxable amount (standard interface)."""
        return self.calculate_ksa_vat(taxable_amount, tax_category)

    # ---------------------------------------------------------------
    # VAT Calculation for KSA
    # ---------------------------------------------------------------

    def calculate_ksa_vat(
        self,
        taxable_amount: float,
        tax_category: str | None = None,
    ) -> dict:
        """
        Calculate Saudi VAT for a taxable amount.

        Categories:
        - standard: 15% VAT
        - exempt: 0% VAT (exempt categories)
        - zero: 0% VAT (zero-rated, e.g. exports)
        """
        category = (tax_category or "standard").lower()

        if category in ("exempt", "exempt_categories") or category in self.VAT_EXEMPT_CATEGORIES:
            rate = self.SAR_ZERO_RATE
            vat_type = "exempt"
        elif category in ("zero", "zero_rated", "exported_goods", "exports"):
            rate = self.SAR_ZERO_RATE
            vat_type = "zero"
        else:
            rate = self.SAR_VAT_RATE
            vat_type = "standard"

        vat_amount = round(taxable_amount * rate / 100, 2)
        total = round(taxable_amount + vat_amount, 2)

        return {
            "country_code": self.KSA_CODE,
            "currency": self.KSA_CURRENCY,
            "tax_type": f"vat_{vat_type}",
            "tax_name": self._get_vat_name(vat_type),
            "taxable_amount": taxable_amount,
            "vat_rate": rate,
            "vat_amount": vat_amount,
            "total_amount": total,
            "resource_type": "vat_calculation",
            "execution_id": None,
            "trace_id": None,
            "category": category,
        }

    def _get_vat_name(self, vat_type: str) -> str:
        """Get Arabic VAT name for KSA"""
        names = {
            "standard": "ضريبة القيمة المضافة السعودية 15%",
            "exempt": "معفاة من ضريبة القيمة المضافة",
            "zero": "ضريبة القيمة المضافة بصفر (صادرات)",
        }
        return names.get(vat_type, "ضريبة القيمة المضافة")

    # ---------------------------------------------------------------
    # E-Invoice Generation (ZATCA Fatoora Format)
    # ---------------------------------------------------------------

    def generate_ksa_e_invoice(
        self,
        invoice_data: dict,
    ) -> dict:
        """
        Generate Saudi e-invoice in ZATCA Fatoora format.

        Required fields in invoice_data:
        - invoice_number
        - invoice_date
        - seller_vat_number
        - buyer_vat_number
        - seller_name
        - buyer_name
        - items: list of {description, quantity, unit_price, vat_rate}
        """
        items = invoice_data.get("items", [])

        taxable_amount = 0.0
        vat_amount = 0.0
        item_details = []

        for item in items:
            desc = item.get("description", "")
            qty = item.get("quantity", 1)
            unit_price = item.get("unit_price", 0)
            line_total = round(qty * unit_price, 2)
            vat_rate = item.get("vat_rate", self.SAR_VAT_RATE)

            line_vat = round(line_total * vat_rate / 100, 2)
            line_total_with_vat = round(line_total + line_vat, 2)

            taxable_amount = round(taxable_amount + line_total, 2)
            vat_amount = round(vat_amount + line_vat, 2)

            item_details.append({
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
                "vat_rate": vat_rate,
                "vat_amount": line_vat,
                "total_with_vat": line_total_with_vat,
            })

        total_amount = round(taxable_amount + vat_amount, 2)

        return {
            "invoice_format": "ZATCA_FATOORA",
            "version": "1.0",
            "invoice_number": invoice_data.get("invoice_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "invoice_type": "nominal",
            "seller": {
                "name": invoice_data.get("seller_name"),
                "vat_number": invoice_data.get("seller_vat_number"),
                "address": invoice_data.get("seller_address"),
                "phone": invoice_data.get("seller_phone"),
                "email": invoice_data.get("seller_email"),
            },
            "buyer": {
                "name": invoice_data.get("buyer_name"),
                "vat_number": invoice_data.get("buyer_vat_number"),
                "address": invoice_data.get("buyer_address"),
                "phone": invoice_data.get("buyer_phone"),
                "email": invoice_data.get("buyer_email"),
            },
            "items": item_details,
            "totals": {
                "taxable_amount": taxable_amount,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "currency": self.KSA_CURRENCY,
            },
            "zatca_compliant": True,
            " QR_code_required": True,
            "submission_method": "ZATCA E-Invoice Platform (Fatoora)",
            "digital_signature_required": True,
        }

    # ---------------------------------------------------------------
    # Statutory Reports (KSA)
    # ---------------------------------------------------------------

    def generate_ksa_vat_return_quarterly(
        self,
        tenant_id: str,
        quarter: int,
        fiscal_year: int,
    ) -> dict:
        """Generate Saudi VAT Return for a quarter (ZATCA format)"""
        quarter_months = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12),
        }
        start_month, end_month = quarter_months.get(quarter, (1, 3))
        due_date = datetime(fiscal_year, end_month, 1) + timedelta(days=15)

        return {
            "report_type": "VAT Return Quarterly (ZATCA)",
            "country_code": self.KSA_CODE,
            "fiscal_year": fiscal_year,
            "quarter": quarter,
            "period": f"{fiscal_year}-{start_month:02d}-{end_month:02d}",
            "currency": self.KSA_CURRENCY,
            "template": {
                "total_sales": 0,
                "total_purchases": 0,
                "vat_collected": 0,
                "vat_paid": 0,
                "net_vat_due": 0,
                "vat_refundable": 0,
            },
            "due_date": due_date.strftime("%Y-%m-%d"),
            "submission_method": "ZATCA E-Invoice Platform",
            "required_fields": [
                "Tax Registration Number (TRN)",
                "Period",
                "Total Sales (taxable)",
                "Total Purchases (taxable)",
                "VAT Collected",
                "VAT Paid",
                "Net VAT Due",
            ],
        }

    def generate_ksa_zakat_return_annual(
        self,
        tenant_id: str,
        fiscal_year: int,
    ) -> dict:
        """Generate Saudi Annual Zakat Return"""
        return {
            "report_type": "Zakat Return Annual",
            "country_code": self.KSA_CODE,
            "fiscal_year": fiscal_year,
            "currency": self.KSA_CURRENCY,
            "template": {
                "net_assets": 0,
                "zakat_base": 0,
                "zakat_rate": self.ZAKAT_RATE,
                "zakat_due": 0,
            },
            "due_date": f"{fiscal_year}-06-30",
            "submission_method": "ZATCA / Ministry of Commerce",
            "required_fields": [
                "Tax Registration Number (TRN)",
                "Fiscal Year",
                "Net Assets (zakat base)",
                "Zakat Due",
            ],
        }

    def generate_ksa_withholding_tax(
        self,
        tenant_id: str,
        fiscal_year: int,
        month: int,
    ) -> dict:
        """Generate Saudi Withholding Tax Return for a month"""
        return {
            "report_type": "Withholding Tax Return",
            "country_code": self.KSA_CODE,
            "fiscal_year": fiscal_year,
            "month": month,
            "currency": self.KSA_CURRENCY,
            "template": {
                "total_payments": 0,
                "tax_withheld": 0,
                "net_tax_due": 0,
            },
            "due_date": f"{fiscal_year}-{month:02d}-15",
            "submission_method": "ZATCA Portal",
            "required_fields": [
                "Tax Registration Number (TRN)",
                "Period (month/year)",
                "Total Payments",
                "Tax Withheld",
                "Net Tax Due",
            ],
        }

    # ---------------------------------------------------------------
    # Zakat Calculation
    # ---------------------------------------------------------------

    def calculate_zakat(self, net_assets: float) -> dict:
        """Calculate Zakat on net assets at 2.5% (simplified)"""
        zakat_due = round(net_assets * self.ZAKAT_RATE / 100, 2)
        return {
            "country_code": self.KSA_CODE,
            "currency": self.KSA_CURRENCY,
            "net_assets": net_assets,
            "zakat_rate": self.ZAKAT_RATE,
            "zakat_due": zakat_due,
        }
