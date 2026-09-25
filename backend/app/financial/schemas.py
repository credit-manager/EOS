from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense"}
NORMAL_BALANCES = {"debit", "credit"}
FISCAL_PERIOD_STATUSES = {"open", "closed", "locked"}
LEDGER_ENTRY_STATUSES = {"draft", "posted", "reversed"}


# ============================================================
# Account
# ============================================================

class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    account_type: str
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, value: str) -> str:
        value = value.lower()
        if value not in ACCOUNT_TYPES:
            raise ValueError("account_type must be asset, liability, equity, revenue, or expense")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()
        if not value.isalpha():
            raise ValueError("currency must be a 3-letter ISO-style code")
        return value


class AccountResponse(AccountCreate):
    id: UUID
    tenant_id: UUID


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    account_type: str | None = None
    is_active: bool | None = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.lower()
        if value not in ACCOUNT_TYPES:
            raise ValueError("account_type must be asset, liability, equity, revenue, or expense")
        return value


# ============================================================
# Journal Entry
# ============================================================

class JournalLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    description: str | None = Field(default=None, max_length=500)
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def validate_side(self) -> "JournalLineCreate":
        debit = self.debit.quantize(Decimal("0.000001"))
        credit = self.credit.quantize(Decimal("0.000001"))
        if debit == 0 and credit == 0:
            raise ValueError("each journal line must contain a debit or credit")
        if debit > 0 and credit > 0:
            raise ValueError("a journal line cannot contain both debit and credit")
        self.debit = debit
        self.credit = credit
        return self


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounting_date: date
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=1000)
    reference: str | None = Field(default=None, max_length=200)
    lines: list[JournalLineCreate] = Field(min_length=2, max_length=200)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()
        if not value.isalpha():
            raise ValueError("currency must be a 3-letter ISO-style code")
        return value


class JournalLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    line_number: int
    description: str | None
    debit: Decimal
    credit: Decimal


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_number: int
    accounting_date: date
    currency: str
    description: str
    reference: str | None
    status: str
    posted_at: str | None
    lines: list[JournalLineResponse]


class TrialBalanceLine(BaseModel):
    account_id: UUID
    code: str
    name: str
    account_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class TrialBalanceResponse(BaseModel):
    currency: str
    lines: list[TrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal


# ============================================================
# Customer (AR)
# ============================================================

class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms: str = Field(default="NET30", max_length=20)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0)
    ar_account_id: UUID | None = None
    is_active: bool = True


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    email: str | None
    phone: str | None
    address: str | None
    tax_id: str | None
    payment_terms: str
    currency: str
    credit_limit: Decimal
    ar_account_id: UUID | None
    is_active: bool


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    payment_terms: str | None = None
    credit_limit: Decimal | None = None
    ar_account_id: UUID | None = None
    is_active: bool | None = None


# ============================================================
# Supplier (AP)
# ============================================================

class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms: str = Field(default="NET30", max_length=20)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    ap_account_id: UUID | None = None
    is_active: bool = True


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    email: str | None
    phone: str | None
    address: str | None
    tax_id: str | None
    payment_terms: str
    currency: str
    ap_account_id: UUID | None
    is_active: bool


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    payment_terms: str | None = None
    ap_account_id: UUID | None = None
    is_active: bool | None = None


# ============================================================
# Invoice (AR)
# ============================================================

class InvoiceLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    account_id: UUID | None = None


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    issue_date: date
    due_date: date
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = None
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1, max_length=100)


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    account_id: UUID | None
    line_total: Decimal


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    invoice_number: str
    customer_id: UUID
    status: str
    issue_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    description: str | None
    notes: str | None
    journal_entry_id: UUID | None
    created_by: UUID
    lines: list[InvoiceLineResponse] = []


# ============================================================
# Bill (AP)
# ============================================================

class BillLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    account_id: UUID | None = None


class BillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID
    issue_date: date
    due_date: date
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = None
    notes: str | None = None
    lines: list[BillLineCreate] = Field(min_length=1, max_length=100)


class BillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    account_id: UUID | None
    line_total: Decimal


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    bill_number: str
    supplier_id: UUID
    status: str
    issue_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    description: str | None
    notes: str | None
    journal_entry_id: UUID | None
    created_by: UUID
    lines: list[BillLineResponse] = []


# ============================================================
# Payment
# ============================================================

class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_type: str = Field(pattern=r"^(customer|supplier)$")
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    payment_date: date
    currency: str = Field(default="USD", min_length=3, max_length=3)
    amount: Decimal = Field(gt=0)
    payment_method: str = Field(default="bank_transfer", max_length=50)
    reference: str | None = Field(default=None, max_length=200)
    bank_account_id: UUID | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    payment_number: str
    payment_type: str
    customer_id: UUID | None
    supplier_id: UUID | None
    status: str
    payment_date: date
    currency: str
    amount: Decimal
    payment_method: str
    reference: str | None
    bank_account_id: UUID | None
    journal_entry_id: UUID | None
    created_by: UUID


class PaymentAllocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: UUID | None = None
    bill_id: UUID | None = None
    amount: Decimal = Field(gt=0)


class AllocatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocations: list[PaymentAllocationCreate] = Field(min_length=1)


# ============================================================
# Bank Account
# ============================================================

class BankAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_number: str = Field(min_length=1, max_length=50)
    account_name: str = Field(min_length=1, max_length=200)
    bank_name: str | None = Field(default=None, max_length=200)
    bank_code: str | None = Field(default=None, max_length=50)
    account_type: str = Field(default="checking", max_length=20)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    gl_account_id: UUID


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_number: str
    account_name: str
    bank_name: str | None
    bank_code: str | None
    account_type: str
    currency: str
    gl_account_id: UUID
    current_balance: Decimal
    last_reconciled_date: date | None
    is_active: bool


# ============================================================
# Bank Transaction
# ============================================================

class BankTransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_account_id: UUID
    transaction_date: date
    value_date: date | None = None
    description: str = Field(min_length=1, max_length=500)
    reference: str | None = Field(default=None, max_length=200)
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)
    balance: Decimal = Field(default=Decimal("0"))


class BankTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    bank_account_id: UUID
    transaction_date: date
    value_date: date | None
    description: str
    reference: str | None
    debit: Decimal
    credit: Decimal
    balance: Decimal
    status: str
    matched_journal_entry_id: UUID | None


class MatchTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journal_entry_id: UUID | None = None


# ============================================================
# Bank Reconciliation
# ============================================================

class ReconciliationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_account_id: UUID
    statement_date: date
    statement_balance: Decimal


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    bank_account_id: UUID
    statement_date: date
    statement_balance: Decimal
    book_balance: Decimal
    difference: Decimal
    status: str
    reconciled_by: UUID | None
    reconciled_at: str | None


# ============================================================
# Financial Statements
# ============================================================

class PnLLine(BaseModel):
    code: str
    name: str
    balance: Decimal


class PnLSection(BaseModel):
    lines: list[PnLLine]
    total: Decimal


class ProfitAndLossResponse(BaseModel):
    currency: str
    revenue: PnLSection
    expense: PnLSection
    gross_profit: Decimal
    net_income: Decimal


class BalanceSheetLine(BaseModel):
    code: str
    name: str
    balance: Decimal


class BalanceSheetSection(BaseModel):
    lines: list[BalanceSheetLine]
    total: Decimal


class BalanceSheetResponse(BaseModel):
    currency: str
    assets: BalanceSheetSection
    liabilities: BalanceSheetSection
    equity: BalanceSheetSection
    total_liabilities_and_equity: Decimal
    is_balanced: bool


class AgingBuckets(BaseModel):
    current: Decimal
    one_thirty: Decimal = Field(alias="1_30")
    thirty_one_sixty: Decimal = Field(alias="31_60")
    sixty_one_ninety: Decimal = Field(alias="61_90")
    over_ninety: Decimal = Field(alias="over_90")

    model_config = ConfigDict(populate_by_name=True)


class AgingResponse(BaseModel):
    as_of: str
    buckets: dict
    total_outstanding: Decimal


class BankAccountSummary(BaseModel):
    bank_account_id: UUID
    account_name: str
    current_balance: Decimal
    inflow: Decimal
    outflow: Decimal


class CashFlowResponse(BaseModel):
    currency: str
    accounts: list[BankAccountSummary]
    total_inflow: Decimal
    total_outflow: Decimal
    net_cash_flow: Decimal


# ============================================================
# Ledger — Chart of Accounts
# ============================================================

class LedgerAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_code: str = Field(min_length=1, max_length=20)
    account_name: str = Field(min_length=1, max_length=200)
    account_type: str
    normal_balance: str
    parent_account_id: UUID | None = None
    is_active: bool = True
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, value: str) -> str:
        value = value.lower()
        if value not in ACCOUNT_TYPES:
            raise ValueError("account_type must be asset, liability, equity, revenue, or expense")
        return value

    @field_validator("normal_balance")
    @classmethod
    def validate_normal_balance(cls, value: str) -> str:
        value = value.lower()
        if value not in NORMAL_BALANCES:
            raise ValueError("normal_balance must be debit or credit")
        return value


class LedgerAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_code: str
    account_name: str
    account_type: str
    normal_balance: str
    parent_account_id: UUID | None
    is_active: bool
    currency: str
    description: str | None


class LedgerAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str | None = Field(default=None, min_length=1, max_length=200)
    account_type: str | None = None
    normal_balance: str | None = None
    parent_account_id: UUID | None = None
    is_active: bool | None = None
    description: str | None = None


# ============================================================
# Ledger — Journal Entry
# ============================================================

class LedgerLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    description: str | None = Field(default=None, max_length=500)
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def validate_side(self) -> "LedgerLineCreate":
        debit = self.debit.quantize(Decimal("0.000001"))
        credit = self.credit.quantize(Decimal("0.000001"))
        if debit == 0 and credit == 0:
            raise ValueError("each line must contain a debit or credit")
        if debit > 0 and credit > 0:
            raise ValueError("a line cannot contain both debit and credit")
        self.debit = debit
        self.credit = credit
        return self


class LedgerEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_date: date
    description: str = Field(min_length=1, max_length=1000)
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: UUID | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    lines: list[LedgerLineCreate] = Field(min_length=2, max_length=200)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()
        if not value.isalpha():
            raise ValueError("currency must be a 3-letter ISO-style code")
        return value


class LedgerLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    line_number: int
    description: str | None
    debit: Decimal
    credit: Decimal


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_number: int
    entry_date: date
    description: str
    reference_type: str | None
    reference_id: UUID | None
    currency: str
    status: str
    posted_by: UUID | None
    posted_at: str | None
    reversed_by_entry_id: UUID | None
    period_id: UUID | None
    lines: list[LedgerLineResponse]


# ============================================================
# Ledger — Account Balance
# ============================================================

class AccountBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    period_id: UUID
    opening_balance: Decimal
    debit_total: Decimal
    credit_total: Decimal
    closing_balance: Decimal


# ============================================================
# Ledger — Posting Rule
# ============================================================

class PostingRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_name: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    debit_account_code: str = Field(min_length=1, max_length=20)
    credit_account_code: str = Field(min_length=1, max_length=20)
    amount_field: str = Field(min_length=1, max_length=100)
    conditions: dict | None = None
    is_active: bool = True


class PostingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_name: str
    event_type: str
    description: str | None
    debit_account_code: str
    credit_account_code: str
    amount_field: str
    conditions: dict | None
    is_active: bool


# ============================================================
# Ledger — Fiscal Period
# ============================================================

class FiscalPeriodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_name: str = Field(min_length=1, max_length=20)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "FiscalPeriodCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class FiscalPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    period_name: str
    start_date: date
    end_date: date
    status: str
    closed_by: UUID | None
    closed_at: str | None


# ============================================================
# Ledger — Trial Balance & Reports
# ============================================================

class LedgerTrialBalanceLine(BaseModel):
    account_id: UUID
    code: str
    name: str
    account_type: str
    normal_balance: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class LedgerTrialBalanceResponse(BaseModel):
    currency: str
    lines: list[LedgerTrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


class LedgerBalanceSheetSection(BaseModel):
    lines: list[dict]
    total: Decimal


class LedgerBalanceSheetResponse(BaseModel):
    currency: str
    assets: LedgerBalanceSheetSection
    liabilities: LedgerBalanceSheetSection
    equity: LedgerBalanceSheetSection
    total_liabilities_and_equity: Decimal
    is_balanced: bool


class LedgerIncomeStatementSection(BaseModel):
    lines: list[dict]
    total: Decimal


class LedgerIncomeStatementResponse(BaseModel):
    currency: str
    revenue: LedgerIncomeStatementSection
    expense: LedgerIncomeStatementSection
    gross_profit: Decimal
    net_income: Decimal
