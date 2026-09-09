"""
EOS Industry Engine — Accounting Mapping
Maps operations to journal entries per industry.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class JournalType(str, Enum):
    SALES = "sales"
    PURCHASE = "purchase"
    PAYMENT = "payment"
    RECEIPT = "receipt"
    JOURNAL = "journal"
    STOCK = "stock"
    PAYROLL = "payroll"
    FIXED_ASSET = "fixed_asset"
    PRODUCTION = "production"


class PostingTrigger(str, Enum):
    ON_CREATE = "on_create"
    ON_APPROVE = "on_approve"
    ON_POST = "on_post"
    ON_COMPLETE = "on_complete"
    MANUAL = "manual"


@dataclass
class AccountMapping:
    """Maps a business event to debit/credit accounts."""
    code: str
    name: str
    name_ar: str
    event: str                        # e.g. "sales_invoice", "purchase_order"
    journal_type: JournalType
    debit_account: str                # Account code pattern
    credit_account: str
    amount_field: str = "total"       # Which field contains the amount
    tax_field: str = "tax_amount"     # Which field contains tax
    cost_center_field: str = ""       # Which field contains cost center
    description_template: str = ""    # e.g. "Invoice {number}"
    posting_trigger: PostingTrigger = PostingTrigger.ON_APPROVE
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndustryAccountingMapping:
    """Accounting mappings for a specific industry."""
    industry: str
    mappings: List[AccountMapping] = field(default_factory=list)
    # Account code patterns
    account_patterns: Dict[str, str] = field(default_factory=dict)
    # Tax configuration
    tax_config: Dict[str, Any] = field(default_factory=dict)


class AccountingMappingEngine:
    """
    Manages accounting mappings per industry.
    Each operation generates the correct journal entries automatically.
    """

    def __init__(self):
        self._mappings: Dict[str, IndustryAccountingMapping] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core accounting mappings."""
        core_mappings = IndustryAccountingMapping(
            industry="core",
            mappings=[
                # Sales Invoice
                AccountMapping(
                    code="SALES_INVOICE", name="Sales Invoice", name_ar="فاتورة مبيعات",
                    event="sales_invoice", journal_type=JournalType.SALES,
                    debit_account="1200",  # Accounts Receivable
                    credit_account="4100",  # Sales Revenue
                    amount_field="total",
                    description_template="Sales Invoice {number}",
                ),
                # Customer Payment
                AccountMapping(
                    code="CUSTOMER_PAYMENT", name="Customer Payment", name_ar="دفعة عميل",
                    event="customer_payment", journal_type=JournalType.RECEIPT,
                    debit_account="1100",  # Cash/Bank
                    credit_account="1200",  # Accounts Receivable
                    amount_field="amount",
                    description_template="Payment from {customer}",
                ),
                # Purchase Invoice
                AccountMapping(
                    code="PURCHASE_INVOICE", name="Purchase Invoice", name_ar="فاتورة شراء",
                    event="purchase_invoice", journal_type=JournalType.PURCHASE,
                    debit_account="5100",  # Purchases
                    credit_account="2100",  # Accounts Payable
                    amount_field="total",
                    description_template="Purchase Invoice {number}",
                ),
                # Supplier Payment
                AccountMapping(
                    code="SUPPLIER_PAYMENT", name="Supplier Payment", name_ar="دفعة مورد",
                    event="supplier_payment", journal_type=JournalType.PAYMENT,
                    debit_account="2100",  # Accounts Payable
                    credit_account="1100",  # Cash/Bank
                    amount_field="amount",
                    description_template="Payment to {supplier}",
                ),
                # Stock Receipt
                AccountMapping(
                    code="STOCK_RECEIPT", name="Stock Receipt", name_ar="استلام مخزون",
                    event="stock_receipt", journal_type=JournalType.STOCK,
                    debit_account="1300",  # Inventory
                    credit_account="2100",  # Accounts Payable (GRN)
                    amount_field="total_cost",
                    description_template="Stock receipt {grn_number}",
                ),
                # Stock Issue
                AccountMapping(
                    code="STOCK_ISSUE", name="Stock Issue", name_ar="صرف مخزون",
                    event="stock_issue", journal_type=JournalType.STOCK,
                    debit_account="5200",  # Cost of Goods Sold
                    credit_account="1300",  # Inventory
                    amount_field="total_cost",
                    description_template="Stock issue to {project}",
                ),
            ],
            account_patterns={
                "cash": "1110",
                "bank": "1120",
                "receivable": "1200",
                "payable": "2100",
                "inventory": "1300",
                "sales_revenue": "4100",
                "sales_returns": "4110",
                "purchases": "5100",
                "cogs": "5200",
                "salaries": "6100",
                "rent": "6200",
                "utilities": "6300",
                "depreciation": "6400",
            },
        )
        self._mappings["core"] = core_mappings

        # Construction accounting mappings
        construction_mappings = IndustryAccountingMapping(
            industry="construction",
            mappings=[
                # Project Cost
                AccountMapping(
                    code="PROJECT_COST", name="Project Cost", name_ar="تكلفة المشروع",
                    event="project_cost", journal_type=JournalType.JOURNAL,
                    debit_account="5300",  # Project Cost
                    credit_account="1300",  # Inventory (materials)
                    amount_field="cost_amount",
                    cost_center_field="project_id",
                    description_template="Project cost: {project_name}",
                ),
                # Equipment Depreciation
                AccountMapping(
                    code="EQUIPMENT_DEPRECIATION", name="Equipment Depreciation", name_ar="إهلاك المعدات",
                    event="equipment_depreciation", journal_type=JournalType.FIXED_ASSET,
                    debit_account="6400",  # Depreciation
                    credit_account="1500",  # Equipment
                    amount_field="depreciation_amount",
                    description_template="Equipment depreciation: {equipment_name}",
                ),
                # Progress Certificate
                AccountMapping(
                    code="PROGRESS_CERT", name="Progress Certificate", name_ar="شهادة إنجاز",
                    event="progress_certificate", journal_type=JournalType.SALES,
                    debit_account="1200",  # Receivable
                    credit_account="4200",  # Progress Billing
                    amount_field="certified_amount",
                    description_template="Progress certificate: {cert_number}",
                ),
                # Retention
                AccountMapping(
                    code="RETENTION", name="Retention", name_ar="ضمان أداء",
                    event="retention", journal_type=JournalType.JOURNAL,
                    debit_account="1250",  # Retention Receivable
                    credit_account="4200",  # Progress Billing
                    amount_field="retention_amount",
                    description_template="Retention: {cert_number}",
                ),
                # Subcontractor Payment
                AccountMapping(
                    code="SUB_PAYMENT", name="Subcontractor Payment", name_ar="دفعة مقاول باطن",
                    event="subcontractor_payment", journal_type=JournalType.PAYMENT,
                    debit_account="5310",  # Subcontractor Cost
                    credit_account="2100",  # Payable
                    amount_field="amount",
                    cost_center_field="project_id",
                    description_template="Sub payment: {subcontractor}",
                ),
            ],
            account_patterns={
                "project_cost": "5300",
                "subcontractor_cost": "5310",
                "equipment_cost": "5320",
                "labor_cost": "5330",
                "progress_billing": "4200",
                "retention_receivable": "1250",
                "retention_payable": "2250",
                "advance_payment": "1260",
                "variation_order": "4300",
            },
        )
        self._mappings["construction"] = construction_mappings

        # Trading accounting mappings
        trading_mappings = IndustryAccountingMapping(
            industry="trading",
            mappings=[
                # Sales with discount
                AccountMapping(
                    code="TRADING_SALES", name="Trading Sales", name_ar="مبيعات تجارية",
                    event="trading_sale", journal_type=JournalType.SALES,
                    debit_account="1200",
                    credit_account="4100",
                    amount_field="net_amount",
                    description_template="Sale: {invoice_number}",
                ),
                # GRN
                AccountMapping(
                    code="TRADING_GRN", name="Trading GRN", name_ar="استلام تجاري",
                    event="trading_grn", journal_type=JournalType.STOCK,
                    debit_account="1300",
                    credit_account="2100",
                    amount_field="total_cost",
                    description_template="GRN: {grn_number}",
                ),
            ],
            account_patterns={
                "sales_discount": "4120",
                "purchase_discount": "5120",
                "delivery_cost": "6310",
            },
        )
        self._mappings["trading"] = trading_mappings

        # Tourism accounting mappings
        tourism_mappings = IndustryAccountingMapping(
            industry="tourism",
            mappings=[
                # Booking Payment (Customer Deposit)
                AccountMapping(
                    code="BOOKING_DEPOSIT", name="Booking Deposit", name_ar="دفعة حجز",
                    event="booking_deposit", journal_type=JournalType.RECEIPT,
                    debit_account="1100",  # Cash/Bank
                    credit_account="2150",  # Customer Deposits (Liability)
                    amount_field="deposit_amount",
                    description_template="Deposit for booking {booking_number}",
                    posting_trigger=PostingTrigger.ON_CREATE,
                ),
                # Booking Confirmation (Revenue Recognition)
                AccountMapping(
                    code="BOOKING_REVENUE", name="Booking Revenue", name_ar="إيراد الحجز",
                    event="booking_confirmed", journal_type=JournalType.SALES,
                    debit_account="1200",  # Accounts Receivable
                    credit_account="4100",  # Tourism Revenue
                    amount_field="total_amount",
                    description_template="Booking revenue: {booking_number}",
                    posting_trigger=PostingTrigger.ON_APPROVE,
                ),
                # Hotel Cost
                AccountMapping(
                    code="HOTEL_COST", name="Hotel Cost", name_ar="تكلفة الفندق",
                    event="hotel_booking_cost", journal_type=JournalType.PURCHASE,
                    debit_account="5100",  # Hotel Costs
                    credit_account="2100",  # Accounts Payable (Hotel)
                    amount_field="hotel_cost",
                    cost_center_field="booking_id",
                    description_template="Hotel cost for booking: {booking_number}",
                ),
                # Flight Cost
                AccountMapping(
                    code="FLIGHT_COST", name="Flight Cost", name_ar="تكلفة الطيران",
                    event="flight_ticket_cost", journal_type=JournalType.PURCHASE,
                    debit_account="5110",  # Flight Costs
                    credit_account="2100",  # Accounts Payable (Airline)
                    amount_field="flight_cost",
                    cost_center_field="booking_id",
                    description_template="Flight cost for booking: {booking_number}",
                ),
                # Commission Revenue
                AccountMapping(
                    code="COMMISSION_REVENUE", name="Commission Revenue", name_ar="إيراد العمولة",
                    event="commission_received", journal_type=JournalType.SALES,
                    debit_account="1200",  # Receivable (from supplier)
                    credit_account="4200",  # Commission Revenue
                    amount_field="commission_amount",
                    description_template="Commission on booking: {booking_number}",
                ),
                # Visa Fee Revenue
                AccountMapping(
                    code="VISA_FEE", name="Visa Fee", name_ar="رسوم التأشيرة",
                    event="visa_fee_collected", journal_type=JournalType.SALES,
                    debit_account="1200",  # Receivable
                    credit_account="4300",  # Service Fees Revenue
                    amount_field="visa_fee",
                    description_template="Visa fee: {visa_number} - {passenger_name}",
                ),
                # Transfer Service Revenue
                AccountMapping(
                    code="TRANSFER_REVENUE", name="Transfer Revenue", name_ar="إيراد الانتقال",
                    event="transfer_service", journal_type=JournalType.SALES,
                    debit_account="1200",  # Receivable
                    credit_account="4400",  # Transfer Services Revenue
                    amount_field="transfer_amount",
                    description_template="Transfer service: {transfer_number}",
                ),
                # Tour Guide Payment
                AccountMapping(
                    code="GUIDE_PAYMENT", name="Guide Payment", name_ar="دفع للمرشد",
                    event="guide_payment", journal_type=JournalType.PAYMENT,
                    debit_account="5120",  # Guide Costs
                    credit_account="1100",  # Cash/Bank
                    amount_field="guide_fee",
                    description_template="Guide payment: {guide_name} - {booking_number}",
                ),
                # Cancellation Refund
                AccountMapping(
                    code="CANCELLATION_REFUND", name="Cancellation Refund", name_ar="استرداد الإلغاء",
                    event="booking_cancelled", journal_type=JournalType.PAYMENT,
                    debit_account="4150",  # Sales Returns & Allowances
                    credit_account="1100",  # Cash/Bank
                    amount_field="refund_amount",
                    description_template="Refund for cancelled booking: {booking_number}",
                ),
            ],
            account_patterns={
                "cash": "1110",
                "bank": "1120",
                "receivable": "1200",
                "customer_deposits": "2150",
                "payable_hotel": "2110",
                "payable_airline": "2120",
                "tourism_revenue": "4100",
                "commission_revenue": "4200",
                "service_fees": "4300",
                "transfer_revenue": "4400",
                "sales_returns": "4150",
                "hotel_costs": "5100",
                "flight_costs": "5110",
                "guide_costs": "5120",
                "visa_costs": "5130",
                "transport_costs": "5140",
            },
            tax_config={
                "vat_rate": 0.15,  # 15% VAT for tourism services
                "tax_exempt_services": ["umrah", "hajj"],  # Religious tourism may be exempt
            },
        )
        self._mappings["tourism"] = tourism_mappings

    def register(self, mapping: IndustryAccountingMapping):
        """Register industry accounting mappings."""
        self._mappings[mapping.industry] = mapping

    def get(self, industry: str) -> Optional[IndustryAccountingMapping]:
        """Get accounting mapping for an industry."""
        return self._mappings.get(industry)

    def get_mapping(self, industry: str, event: str) -> Optional[AccountMapping]:
        """Get specific mapping for an event in an industry."""
        mapping = self._mappings.get(industry)
        if not mapping:
            mapping = self._mappings.get("core")
        if not mapping:
            return None

        for m in mapping.mappings:
            if m.event == event:
                return m
        return None

    def get_account_code(self, industry: str, pattern: str) -> str:
        """Resolve account code pattern to actual code."""
        mapping = self._mappings.get(industry)
        if not mapping:
            mapping = self._mappings.get("core")
        if mapping:
            return mapping.account_patterns.get(pattern, pattern)
        return pattern

    def generate_journal_entry(self, industry: str, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate journal entry lines for a business event.
        Returns dict with debit_lines and credit_lines.
        """
        mapping = self.get_mapping(industry, event)
        if not mapping:
            return {"error": f"No mapping for event '{event}' in industry '{industry}'"}

        amount = float(data.get(mapping.amount_field, 0))
        tax = float(data.get(mapping.tax_field, 0))
        total = amount + tax

        debit_account = self.get_account_code(industry, mapping.debit_account)
        credit_account = self.get_account_code(industry, mapping.credit_account)

        lines = []
        if amount > 0:
            lines.append({
                "account_code": debit_account,
                "debit": amount,
                "credit": 0,
                "description": mapping.description_template.format(**data) if data else mapping.name,
                "cost_center": data.get(mapping.cost_center_field, ""),
            })
            lines.append({
                "account_code": credit_account,
                "debit": 0,
                "credit": amount,
                "description": mapping.description_template.format(**data) if data else mapping.name,
                "cost_center": data.get(mapping.cost_center_field, ""),
            })

        if tax > 0:
            # Tax payable line
            lines.append({
                "account_code": self.get_account_code(industry, "tax_payable"),
                "debit": 0,
                "credit": tax,
                "description": f"Tax on {mapping.name}",
            })

        return {
            "journal_type": mapping.journal_type.value,
            "description": mapping.description_template.format(**data) if data else mapping.name,
            "lines": lines,
            "total_debit": sum(l["debit"] for l in lines),
            "total_credit": sum(l["credit"] for l in lines),
        }

    def get_all_events(self, industry: str) -> List[str]:
        """Get all bookable events for an industry."""
        mapping = self._mappings.get(industry)
        if not mapping:
            return []
        return [m.event for m in mapping.mappings]

    def export_mappings(self, industry: str) -> List[Dict[str, Any]]:
        """Export mappings for templates."""
        mapping = self._mappings.get(industry)
        if not mapping:
            return []
        return [{
            "code": m.code, "name": m.name, "name_ar": m.name_ar,
            "event": m.event, "journal_type": m.journal_type.value,
            "debit_account": m.debit_account, "credit_account": m.credit_account,
            "amount_field": m.amount_field, "posting_trigger": m.posting_trigger.value,
        } for m in mapping.mappings]
