"""
Egypt Pack - reference implementation for Globalization Engine.

Provides Egypt-specific:
- Tax rules (VAT 14%, reduced rates, exemptions)
- E-invoice formatting per Egyptian Tax Authority (ETA) standards
- Statutory reports (VAT return, income tax, social insurance)
- Fiscal calendar (Egypt fiscal year)
- Numbering conventions
- Currency formatting (EGP)
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Country, CountryPack, Currency, TaxConfig

logger = logging.getLogger("2to-eos.globalization.egypt")


class EgyptPackService:
    """
    Egypt Pack implementation.

    Reference implementation showing how a country pack should work:
    - Tax calculation with Egyptian VAT rules
    - E-invoice generation in ETA format
    - Statutory report generation
    - Egypt fiscal calendar (Jan 1 - Dec 31)
    """

    EGYPT_CODE = "EG"
    EGYPT_CURRENCY = "EGP"
    EGP_VAT_RATE = 14.0
    EGP_REDUCED_VAT_RATE = 5.0
    EGP_ZERO_RATE = 0.0

    # Egyptian VAT categories
    VAT_EXEMPT_CATEGORIES = [
        "agricultural_products",
        "educational_services",
        "medical_services",
        "real_estate_leasing",
        "financial_services",
        "residential_building",
        "consular_diploatic",
    ]

    VAT_REDUCED_CATEGORIES = [
        "tourist_services",
        "some_food_items",
    ]

    # Egyptian fiscal year
    FISCAL_YEAR_START = 1  # January
    FISCAL_YEAR_END = 12   # December

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------------
    # Country & Pack Management
    # ---------------------------------------------------------------

    def ensure_egypt_country(self) -> Country:
        """Ensure Egypt country record exists"""
        country = self.db.scalar(
            select(Country).where(Country.code == self.EGYPT_CODE)
        )
        if country:
            return country

        country = Country(
            code=self.EGYPT_CODE,
            name="Egypt",
            native_name="مصر",
            currency_code=self.EGYPT_CURRENCY,
            currency_name="Egyptian Pound",
            currency_symbol="EGP",
            language_code="ar",
            language_name="Arabic",
            timezone="Africa/Cairo",
            phone_code="+20",
            date_format="DD/MM/YYYY",
            number_format="#,##0.00",
        )
        self.db.add(country)
        self.db.commit()
        self.db.refresh(country)
        logger.info("Egypt country record created")
        return country

    def ensure_egypt_currency(self) -> Currency:
        """Ensure EGP currency record exists"""
        currency = self.db.scalar(
            select(Currency).where(Currency.code == self.EGYPT_CURRENCY)
        )
        if currency:
            return currency

        currency = Currency(
            code=self.EGYPT_CURRENCY,
            name="Egyptian Pound",
            symbol="ج.م.",
            decimal_places=2,
        )
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        logger.info("EGP currency record created")
        return currency

    def ensure_egypt_pack(self) -> CountryPack:
        """Ensure Egypt pack exists with full configuration"""
        pack = self.db.scalar(
            select(CountryPack).where(
                CountryPack.country_code == self.EGYPT_CODE,
                CountryPack.is_active.is_(True)
            )
        )
        if pack:
            return pack

        pack = CountryPack(
            country_code=self.EGYPT_CODE,
            pack_name="Egypt Pack",
            pack_version="1.0.0",
            pack_config={
                "country_code": self.EGYPT_CODE,
                "currency": self.EGYPT_CURRENCY,
                "language": "ar",
                "timezone": "Africa/Cairo",
                "date_format": "DD/MM/YYYY",
                "number_format": "#,##0.00",
                "fiscal_year_start_month": self.FISCAL_YEAR_START,
                "fiscal_year_end_month": self.FISCAL_YEAR_END,
            },
            tax_config={
                "vat_rate": self.EGP_VAT_RATE,
                "reduced_vat_rate": self.EGP_REDUCED_VAT_RATE,
                "zero_rated": self.EGP_ZERO_RATE,
                "exempt_categories": self.VAT_EXEMPT_CATEGORIES,
                "reduced_categories": self.VAT_REDUCED_CATEGORIES,
            },
            accounting_config={
                "currency": self.EGYPT_CURRENCY,
                "fiscal_year_start": self.FISCAL_YEAR_START,
                "fiscal_year_end": self.FISCAL_YEAR_END,
                "accounting_basis": "accrual",
            },
            e_invoice_config={
                "standard": "Egyptian Tax Authority (ETA) e-invoice standard",
                "version": "1.0",
                "integration": "ETA Portal API",
                "authorization_required": True,
                "invoice_types": ["standard", "credit_note", "debit_note"],
                "required_fields": [
                    "invoice_number",
                    "invoice_date",
                    "seller_tax_id",
                    "buyer_tax_id",
                    "taxable_amount",
                    "vat_amount",
                    "total_amount",
                ],
            },
            compliance_config={
                "statutory_reports": [
                    "VAT Return Quarterly",
                    "Income Tax Return Annual",
                    "Employee Withholding Tax",
                    "Social Insurance Returns",
                ],
                "audit_trail_required": True,
                "invoice_retention_years": 5,
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
                    "title": "إقرار ضريبة القيمة المضافة ربعي",
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
                "income_tax_annual": {
                    "title": "إقرار ضريبة الدخل السنوي",
                    "frequency": "Annual",
                    "due_days_after_year_end": 120,
                    "required_data": [
                        "gross_revenue",
                        "deductible_expenses",
                        "net_profit",
                        "taxable_income",
                        "tax_due",
                    ],
                },
                "employee_withholding_tax": {
                    "title": "ضريبة الدخل المخصوم من الرواتب",
                    "frequency": "Monthly",
                    "due_days_after_period": 15,
                    "required_data": [
                        "total_salaries",
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
        logger.info("Egypt Pack created")
        return pack

    # ---------------------------------------------------------------
    # Unified interface methods (for pack registry)
    # ---------------------------------------------------------------

    def ensure_country(self) -> Country:
        """Unified interface: ensure Egypt country record."""
        return self.ensure_egypt_country()

    def ensure_currency(self) -> Currency:
        """Unified interface: ensure EGP currency record."""
        return self.ensure_egypt_currency()

    def ensure_pack(self) -> CountryPack:
        """Unified interface: ensure Egypt pack record."""
        return self.ensure_egypt_pack()

    def ensure_tax_configs(self) -> list[TaxConfig]:
        """Unified interface: ensure Egypt tax configs."""
        return self._ensure_egypt_tax_configs()

    def _ensure_egypt_tax_configs(self) -> list[TaxConfig]:
        """Create Egypt VAT and reduced-tax configurations"""
        configs = []
        tax_definitions = [
            {
                "tax_type": "vat_standard",
                "tax_name": "ضريبة القيمة المضافة المصرية (14%)",
                "tax_rate": 14,
                "effective_from": datetime(2016, 10, 1),
            },
            {
                "tax_type": "vat_reduced",
                "tax_name": "ضريبة القيمة المضافة المخفّضة (5%)",
                "tax_rate": 5,
                "effective_from": datetime(2016, 10, 1),
            },
            {
                "tax_type": "vat_zero",
                "tax_name": "ضريبة القيمة المضافة بصفر",
                "tax_rate": 0,
                "effective_from": datetime(2016, 10, 1),
            },
        ]

        for tax_def in tax_definitions:
            existing = self.db.scalar(
                select(TaxConfig).where(
                    TaxConfig.country_code == self.EGYPT_CODE,
                    TaxConfig.tax_type == tax_def["tax_type"],
                )
            )
            if existing:
                configs.append(existing)
                continue

            tax = TaxConfig(
                country_code=self.EGYPT_CODE,
                **tax_def,
            )
            self.db.add(tax)
            configs.append(tax)

        self.db.commit()
        for c in configs:
            self.db.refresh(c)
        logger.info("Egypt tax configs created: %d", len(configs))
        return configs

    # ------------------------------------------------------------------
    # VAT Calculation (common interface)
    # ------------------------------------------------------------------

    def calculate_vat(
        self,
        taxable_amount: float,
        tax_category: str | None = None,
    ) -> dict:
        """Calculate VAT for a taxable amount (standard interface)."""
        return self.calculate_egypt_vat(
            taxable_amount=taxable_amount,
            tax_category=tax_category,
        )

    # ------------------------------------------------------------------
    # VAT Calculation for Egypt
    # ------------------------------------------------------------------

    def calculate_egypt_vat(
        self,
        taxable_amount: float,
        tax_category: str | None = None,
    ) -> dict:
        """
        Calculate Egyptian VAT for a taxable amount.

        Categories:
        - standard: 14% VAT
        - reduced: 5% VAT
        - exempt: 0% VAT (exempt categories)
        - zero: 0% VAT (zero-rated, e.g. exports)
        """
        category = (tax_category or "standard").lower()

        if category in ("exempt", "exempt_categories") or category in self.VAT_EXEMPT_CATEGORIES:
            rate = self.EGP_ZERO_RATE
            vat_type = "exempt"
        elif category in ("zero", "zero_rated", "exported_goods", "exports"):
            rate = self.EGP_ZERO_RATE
            vat_type = "zero"
        elif category in ("reduced", "reduced_categories", " tourist", "tourist"):
            rate = self.EGP_REDUCED_VAT_RATE
            vat_type = "reduced"
        else:
            rate = self.EGP_VAT_RATE
            vat_type = "standard"

        vat_amount = round(taxable_amount * rate / 100, 2)
        total = round(taxable_amount + vat_amount, 2)

        return {
            "country_code": self.EGYPT_CODE,
            "currency": self.EGYPT_CURRENCY,
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
        """Get Arabic VAT name"""
        names = {
            "standard": "ضريبة القيمة المضافة القياسية 14%",
            "reduced": "ضريبة القيمة المضافة المخفّضة 5%",
            "exempt": "معفاة من ضريبة القيمة المضافة",
            "zero": "ضريبة القيمة المضافة بصفر",
        }
        return names.get(vat_type, "ضريبة القيمة المضافة")

    # ---------------------------------------------------------------
    # E-Invoice Generation (ETA Format)
    # ---------------------------------------------------------------

    def generate_egypt_e_invoice(
        self,
        invoice_data: dict,
    ) -> dict:
        """
        Generate Egyptian e-invoice in ETA format.

        Required fields in invoice_data:
        - invoice_number
        - invoice_date
        - seller_name
        - seller_tax_id
        - buyer_name
        - buyer_tax_id
        - items: list of {description, quantity, unit_price, taxable_amount, vat_rate}
        """
        items = invoice_data.get("items", [])

        # Calculate totals
        taxable_amount = 0
        vat_amount = 0
        item_details = []

        for item in items:
            desc = item.get("description", "")
            qty = item.get("quantity", 1)
            unit_price = item.get("unit_price", 0)
            line_total = qty * unit_price
            vat_rate = item.get("vat_rate", self.EGP_VAT_RATE)

            line_vat = int(line_total * vat_rate / 100)
            line_total_with_vat = line_total + line_vat

            taxable_amount += line_total
            vat_amount += line_vat

            item_details.append({
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
                "vat_rate": vat_rate,
                "vat_amount": line_vat,
                "total_with_vat": line_total_with_vat,
            })

        total_amount = taxable_amount + vat_amount

        e_invoice = {
            "invoice_format": "ETA_E_INVOICE",
            "version": "1.0",
            "invoice_number": invoice_data.get("invoice_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "invoice_type": "standard",
            "seller": {
                "name": invoice_data.get("seller_name"),
                "tax_id": invoice_data.get("seller_tax_id"),
                "address": invoice_data.get("seller_address"),
                "phone": invoice_data.get("seller_phone"),
                "email": invoice_data.get("seller_email"),
            },
            "buyer": {
                "name": invoice_data.get("buyer_name"),
                "tax_id": invoice_data.get("buyer_tax_id"),
                "address": invoice_data.get("buyer_address"),
                "phone": invoice_data.get("buyer_phone"),
                "email": invoice_data.get("buyer_email"),
            },
            "items": item_details,
            "totals": {
                "taxable_amount": taxable_amount,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "currency": self.EGYPT_CURRENCY,
            },
            "eta_compliant": True,
            "digital_signature_required": True,
            "submission_deadline": (
                datetime.strptime(invoice_data.get("invoice_date", datetime.now().isoformat()[:10]),
                                  "%Y-%m-%d").strftime("%Y-%m-%d")
                if invoice_data.get("invoice_date")
                else None
            ),
        }

        return e_invoice

    # ---------------------------------------------------------------
    # Statutory Reports (Egypt)
    # ---------------------------------------------------------------

    def generate_vat_return_quarterly(
        self,
        tenant_id: str,
        quarter: int,
        fiscal_year: int,
    ) -> dict:
        """
        Generate Egyptian VAT Return for a quarter.

        VAT returns in Egypt are submitted quarterly.
        Quarters:
        - Q1: Jan-Mar
        - Q2: Apr-Jun
        - Q3: Jul-Sep
        - Q4: Oct-Dec
        """
        quarter_months = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12),
        }

        start_month, end_month = quarter_months.get(quarter, (1, 3))

        # TODO: In production, this would aggregate from actual transactions
        # For now, return template
        return {
            "report_type": "VAT Return Quarterly",
            "country_code": self.EGYPT_CODE,
            "fiscal_year": fiscal_year,
            "quarter": quarter,
            "period": f"{fiscal_year}-{start_month:02d}-{end_month:02d}",
            "currency": self.EGYPT_CURRENCY,
            "template": {
                "total_sales": 0,  # Aggregate from invoices
                "total_purchases": 0,  # Aggregate from bills
                "vat_collected_standard": 0,
                "vat_collected_reduced": 0,
                "vat_paid_standard": 0,
                "vat_paid_reduced": 0,
                "net_vat_due": 0,
                "vat_refundable": 0,
            },
            "due_date": (
                datetime(fiscal_year, end_month, 1) +
                __import__('datetime').timedelta(days=15)
            ).strftime("%Y-%m-%d"),
            "submission_method": "ETA Portal",
            "required_fields": [
                "Tax ID",
                "Period",
                "Total Sales (taxable)",
                "Total Purchases (taxable)",
                "VAT Collected",
                "VAT Paid",
                "Net VAT Due",
            ],
        }

    def generate_income_tax_return_annual(
        self,
        tenant_id: str,
        fiscal_year: int,
    ) -> dict:
        """Generate Egyptian Annual Income Tax Return"""
        # TODO: Aggregate from actual financial data
        return {
            "report_type": "Income Tax Return Annual",
            "country_code": self.EGYPT_CODE,
            "fiscal_year": fiscal_year,
            "currency": self.EGYPT_CURRENCY,
            "template": {
                "gross_revenue": 0,
                "deductible_expenses": 0,
                "net_profit": 0,
                "taxable_income": 0,
                "income_tax_due": 0,
                "tax_already_paid": 0,
                "net_tax_due": 0,
            },
            "due_date": f"{fiscal_year + 1}-06-30",
            "submission_method": "ETA Portal",
            "required_fields": [
                "Tax ID",
                "Fiscal Year",
                "Gross Revenue",
                "Deductible Expenses",
                "Net Profit",
                "Taxable Income",
                "Income Tax Due",
            ],
        }

    def generate_employee_withholding_tax_monthly(
        self,
        tenant_id: str,
        month: int,
        fiscal_year: int,
    ) -> dict:
        """Generate Egyptian Monthly Employee Withholding Tax Report"""
        return {
            "report_type": "Employee Withholding Tax Monthly",
            "country_code": self.EGYPT_CODE,
            "fiscal_year": fiscal_year,
            "month": month,
            "currency": self.EGYPT_CURRENCY,
            "template": {
                "total_salaries": 0,
                "tax_withheld": 0,
                "net_tax_due": 0,
            },
            "due_date": (
                datetime(fiscal_year, month, 1) +
                __import__('datetime').timedelta(days=15)
            ).strftime("%Y-%m-%d"),
            "submission_method": "ETA Portal",
        }

    # ---------------------------------------------------------------
    # Egypt Numbering Sequences
    # ---------------------------------------------------------------

    def get_egypt_numbering_pattern(self, entity_type: str) -> dict:
        """Get Egypt-standard numbering pattern for entity type"""
        patterns = {
            "invoice": {"prefix": "INV", "padding": 6, "suffix": ""},
            "contract": {"prefix": "CON", "padding": 6, "suffix": ""},
            "purchase_order": {"prefix": "PO", "padding": 6, "suffix": ""},
            "quotation": {"prefix": "QUO", "padding": 6, "suffix": ""},
            "payment": {"prefix": "PAY", "padding": 6, "suffix": ""},
            "employee": {"prefix": "EMP", "padding": 4, "suffix": ""},
            "asset": {"prefix": "AST", "padding": 6, "suffix": ""},
        }
        return patterns.get(entity_type, {"prefix": entity_type[:3].upper(), "padding": 6, "suffix": ""})

    # ---------------------------------------------------------------
    # Fiscal Calendar Helpers
    # ---------------------------------------------------------------

    def get_fiscal_year_for_date(self, date: datetime) -> int:
        """Get Egypt fiscal year for a date (calendar year)"""
        return date.year

    def get_quarters_in_year(self, fiscal_year: int) -> list[dict]:
        """Get Egypt fiscal quarters for a year"""
        return [
            {"quarter": 1, "name": "Q1", "start": f"{fiscal_year}-01-01", "end": f"{fiscal_year}-03-31"},
            {"quarter": 2, "name": "Q2", "start": f"{fiscal_year}-04-01", "end": f"{fiscal_year}-06-30"},
            {"quarter": 3, "name": "Q3", "start": f"{fiscal_year}-07-01", "end": f"{fiscal_year}-09-30"},
            {"quarter": 4, "name": "Q4", "start": f"{fiscal_year}-10-01", "end": f"{fiscal_year}-12-31"},
        ]

    def get_current_fiscal_quarter(self, date: datetime | None = None) -> dict:
        """Get current Egypt fiscal quarter"""
        now = date or datetime.now()
        month = now.month

        if month <= 3:
            return {"quarter": 1, "name": "Q1", "start": f"{now.year}-01-01", "end": f"{now.year}-03-31"}
        elif month <= 6:
            return {"quarter": 2, "name": "Q2", "start": f"{now.year}-04-01", "end": f"{now.year}-06-30"}
        elif month <= 9:
            return {"quarter": 3, "name": "Q3", "start": f"{now.year}-07-01", "end": f"{now.year}-09-30"}
        else:
            return {"quarter": 4, "name": "Q4", "start": f"{now.year}-10-01", "end": f"{now.year}-12-31"}


# Singleton service instance factory
def get_egypt_pack_service(db: Session) -> EgyptPackService:
    return EgyptPackService(db)
