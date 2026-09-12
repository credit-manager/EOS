from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense"}


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
    id: UUID
    account_id: UUID
    line_number: int
    description: str | None
    debit: Decimal
    credit: Decimal


class JournalEntryResponse(BaseModel):
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


class ReportAccountLine(BaseModel):
    account_id: UUID
    code: str
    name: str
    amount: Decimal


class ReportGroup(BaseModel):
    lines: list[ReportAccountLine]
    total: Decimal


class BalanceSheetResponse(BaseModel):
    currency: str
    as_of: str | None
    assets: ReportGroup
    liabilities: ReportGroup
    equity: ReportGroup
    total_liabilities_and_equity: Decimal


class IncomeStatementResponse(BaseModel):
    currency: str
    period_start: str | None
    period_end: str | None
    revenue: ReportGroup
    expenses: ReportGroup
    net_income: Decimal


class CashFlowResponse(BaseModel):
    currency: str
    period_start: str | None
    period_end: str | None
    operating: ReportGroup
    investing: ReportGroup
    financing: ReportGroup
    net_change_in_cash: Decimal
