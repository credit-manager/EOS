from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..tenant import require_admin, require_tenant
from .models import (
    Account,
    BankAccount,
    BankReconciliation,
    BankTransaction,
    Bill,
    BillLine,
    Customer,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    Payment,
    Supplier,
)
from .schemas import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    AllocatePaymentRequest,
    AgingResponse,
    BalanceSheetResponse,
    BankAccountCreate,
    BankAccountResponse,
    BankTransactionCreate,
    BankTransactionResponse,
    BillCreate,
    BillResponse,
    CashFlowResponse,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    FiscalPeriodCreate,
    FiscalPeriodResponse,
    InvoiceCreate,
    InvoiceResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalLineResponse,
    LedgerAccountCreate,
    LedgerAccountResponse,
    LedgerAccountUpdate,
    LedgerBalanceSheetResponse,
    LedgerEntryCreate,
    LedgerEntryResponse,
    LedgerIncomeStatementResponse,
    LedgerLineResponse,
    LedgerTrialBalanceResponse,
    MatchTransactionRequest,
    PaymentCreate,
    PaymentResponse,
    PostingRuleCreate,
    PostingRuleResponse,
    ProfitAndLossResponse,
    ReconciliationCreate,
    ReconciliationResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
    TrialBalanceLine,
    TrialBalanceResponse,
)
from .service import (
    allocate_payment,
    commit_financial,
    complete_reconciliation,
    create_bank_account,
    create_bank_transaction,
    create_bill,
    create_customer,
    create_draft,
    create_invoice,
    create_payment,
    create_reconciliation,
    create_supplier,
    get_ap_aging,
    get_ar_aging,
    get_balance_sheet,
    get_bank_account,
    get_bill,
    get_cash_flow,
    get_customer,
    get_invoice,
    get_payment,
    get_profit_and_loss,
    get_supplier,
    list_bank_accounts,
    list_bank_transactions,
    list_bills,
    list_customers,
    list_invoices,
    list_payments,
    list_reconciliations,
    list_suppliers,
    match_bank_transaction,
    post_bill_to_ledger,
    post_entry,
    post_invoice_to_ledger,
    update_bill_status,
    update_customer,
    update_invoice_status,
    update_supplier,
)
from . import ledger as ledger_models
from . import posting_service as ledger_service
from . import trial_balance as reports_service

router = APIRouter(prefix="/api/v1/financial", tags=["financial"])


# ============================================================
# Accounts (existing)
# ============================================================

@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    payload: AccountCreate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Account:
    existing = db.scalar(
        select(Account).where(Account.tenant_id == tenant_id, Account.code == payload.code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="account code already exists")
    account = Account(tenant_id=tenant_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    tenant_id: UUID = Depends(require_admin),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Account]:
    query = select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code)
    if active_only:
        query = query.where(Account.is_active.is_(True))
    return db.scalars(query).all()


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="account not found")
    if payload.name is not None:
        account.name = payload.name
    if payload.account_type is not None:
        account.account_type = payload.account_type
    if payload.is_active is not None:
        account.is_active = payload.is_active
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=204, response_model=None)
def delete_account(
    account_id: UUID,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    account = db.get(Account, account_id)
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="account not found")
    has_lines = db.scalar(
        select(func.count())
        .select_from(JournalLine)
        .where(JournalLine.account_id == account_id)
    )
    if has_lines:
        raise HTTPException(status_code=409, detail="cannot delete account with journal lines")
    db.delete(account)
    db.commit()


# ============================================================
# Journal Entries (existing)
# ============================================================

@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    payload: JournalEntryCreate,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = create_draft(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        payload=payload, request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_entry(db, entry)


@router.post("/journal-entries/{entry_id}/post", response_model=JournalEntryResponse)
def post_journal_entry(
    entry_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = post_entry(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        entry_id=entry_id, request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_entry(db, entry)


@router.get("/journal-entries", response_model=list[JournalEntryResponse])
def list_journal_entries(
    status: str | None = Query(default=None),
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[JournalEntryResponse]:
    query = (
        select(JournalEntry)
        .where(JournalEntry.tenant_id == tenant_id)
        .order_by(JournalEntry.accounting_date.desc(), JournalEntry.id)
    )
    if status is not None:
        query = query.where(JournalEntry.status == status)
    entries = db.scalars(query).all()
    return [_serialize_entry(db, entry) for entry in entries]


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(
    entry_id: UUID,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = db.scalar(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="journal entry not found")
    return _serialize_entry(db, entry)


@router.get("/trial-balance", response_model=TrialBalanceResponse)
def trial_balance(
    tenant_id: UUID = Depends(require_admin),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> TrialBalanceResponse:
    currency = currency.upper()
    rows = db.execute(
        select(
            Account.id, Account.code, Account.name, Account.account_type,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            Account.tenant_id == tenant_id, Account.currency == currency,
            JournalEntry.tenant_id == tenant_id, JournalEntry.currency == currency,
            JournalEntry.status == "posted",
        )
        .group_by(Account.id, Account.code, Account.name, Account.account_type)
        .order_by(Account.code)
    ).all()
    lines: list[TrialBalanceLine] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for account_id, code, name, account_type, debit, credit in rows:
        debit = Decimal(debit or 0)
        credit = Decimal(credit or 0)
        total_debit += debit
        total_credit += credit
        lines.append(
            TrialBalanceLine(
                account_id=account_id, code=code, name=name,
                account_type=account_type, debit=debit, credit=credit,
                balance=debit - credit,
            )
        )
    return TrialBalanceResponse(
        currency=currency, lines=lines,
        total_debit=total_debit, total_credit=total_credit,
    )


# ============================================================
# Customers (AR)
# ============================================================

@router.post("/customers", response_model=CustomerResponse, status_code=201)
def api_create_customer(
    payload: CustomerCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Customer:
    customer = create_customer(db, tenant_id=tenant_id, data=payload.model_dump())
    commit_financial(db)
    return customer


@router.get("/customers", response_model=list[CustomerResponse])
def api_list_customers(
    tenant_id: UUID = Depends(require_tenant),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Customer]:
    return list_customers(db, tenant_id, active_only=active_only)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def api_get_customer(
    customer_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Customer:
    return get_customer(db, tenant_id, customer_id)


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
def api_update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Customer:
    customer = update_customer(db, tenant_id, customer_id, payload.model_dump(exclude_unset=True))
    commit_financial(db)
    return customer


# ============================================================
# Suppliers (AP)
# ============================================================

@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def api_create_supplier(
    payload: SupplierCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = create_supplier(db, tenant_id=tenant_id, data=payload.model_dump())
    commit_financial(db)
    return supplier


@router.get("/suppliers", response_model=list[SupplierResponse])
def api_list_suppliers(
    tenant_id: UUID = Depends(require_tenant),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return list_suppliers(db, tenant_id, active_only=active_only)


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def api_get_supplier(
    supplier_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Supplier:
    return get_supplier(db, tenant_id, supplier_id)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def api_update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = update_supplier(db, tenant_id, supplier_id, payload.model_dump(exclude_unset=True))
    commit_financial(db)
    return supplier


# ============================================================
# Invoices (AR)
# ============================================================

@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def api_create_invoice(
    payload: InvoiceCreate,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Invoice:
    invoice = create_invoice(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        data=payload.model_dump(exclude={"lines"}),
        lines_data=[line.model_dump() for line in payload.lines],
    )
    commit_financial(db)
    return _serialize_invoice(db, invoice)


@router.get("/invoices", response_model=list[InvoiceResponse])
def api_list_invoices(
    tenant_id: UUID = Depends(require_tenant),
    customer_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Invoice]:
    invoices = list_invoices(db, tenant_id, customer_id=customer_id, status=status)
    return [_serialize_invoice(db, inv) for inv in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def api_get_invoice(
    invoice_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Invoice:
    inv = get_invoice(db, tenant_id, invoice_id)
    return _serialize_invoice(db, inv)


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse)
def api_update_invoice_status(
    invoice_id: UUID,
    status: str = Query(...),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Invoice:
    inv = update_invoice_status(db, tenant_id, invoice_id, status)
    commit_financial(db)
    return _serialize_invoice(db, inv)


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceResponse)
def api_post_invoice(
    invoice_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Invoice:
    inv = post_invoice_to_ledger(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        invoice_id=invoice_id, request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_invoice(db, inv)


# ============================================================
# Bills (AP)
# ============================================================

@router.post("/bills", response_model=BillResponse, status_code=201)
def api_create_bill(
    payload: BillCreate,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Bill:
    bill = create_bill(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        data=payload.model_dump(exclude={"lines"}),
        lines_data=[line.model_dump() for line in payload.lines],
    )
    commit_financial(db)
    return _serialize_bill(db, bill)


@router.get("/bills", response_model=list[BillResponse])
def api_list_bills(
    tenant_id: UUID = Depends(require_tenant),
    supplier_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Bill]:
    bills = list_bills(db, tenant_id, supplier_id=supplier_id, status=status)
    return [_serialize_bill(db, b) for b in bills]


@router.get("/bills/{bill_id}", response_model=BillResponse)
def api_get_bill(
    bill_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Bill:
    bill = get_bill(db, tenant_id, bill_id)
    return _serialize_bill(db, bill)


@router.patch("/bills/{bill_id}/status", response_model=BillResponse)
def api_update_bill_status(
    bill_id: UUID,
    status: str = Query(...),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Bill:
    bill = update_bill_status(db, tenant_id, bill_id, status)
    commit_financial(db)
    return _serialize_bill(db, bill)


@router.post("/bills/{bill_id}/post", response_model=BillResponse)
def api_post_bill(
    bill_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Bill:
    bill = post_bill_to_ledger(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        bill_id=bill_id, request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_bill(db, bill)


# ============================================================
# Payments
# ============================================================

@router.post("/payments", response_model=PaymentResponse, status_code=201)
def api_create_payment(
    payload: PaymentCreate,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Payment:
    payment = create_payment(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        data=payload.model_dump(),
    )
    commit_financial(db)
    return payment


@router.get("/payments", response_model=list[PaymentResponse])
def api_list_payments(
    tenant_id: UUID = Depends(require_tenant),
    payment_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Payment]:
    return list_payments(db, tenant_id, payment_type=payment_type, status=status)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def api_get_payment(
    payment_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Payment:
    return get_payment(db, tenant_id, payment_id)


@router.post("/payments/{payment_id}/allocate", response_model=PaymentResponse)
def api_allocate_payment(
    payment_id: UUID,
    payload: AllocatePaymentRequest,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Payment:
    payment = allocate_payment(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        payment_id=payment_id,
        allocations=[a.model_dump() for a in payload.allocations],
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return payment


# ============================================================
# Bank Accounts
# ============================================================

@router.post("/bank-accounts", response_model=BankAccountResponse, status_code=201)
def api_create_bank_account(
    payload: BankAccountCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankAccount:
    ba = create_bank_account(db, tenant_id=tenant_id, data=payload.model_dump())
    commit_financial(db)
    return ba


@router.get("/bank-accounts", response_model=list[BankAccountResponse])
def api_list_bank_accounts(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BankAccount]:
    return list_bank_accounts(db, tenant_id)


@router.get("/bank-accounts/{bank_account_id}", response_model=BankAccountResponse)
def api_get_bank_account(
    bank_account_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankAccount:
    return get_bank_account(db, tenant_id, bank_account_id)


# ============================================================
# Bank Transactions
# ============================================================

@router.post("/bank-transactions", response_model=BankTransactionResponse, status_code=201)
def api_create_bank_transaction(
    payload: BankTransactionCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankTransaction:
    bt = create_bank_transaction(db, tenant_id=tenant_id, data=payload.model_dump())
    commit_financial(db)
    return bt


@router.get("/bank-transactions", response_model=list[BankTransactionResponse])
def api_list_bank_transactions(
    tenant_id: UUID = Depends(require_tenant),
    bank_account_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[BankTransaction]:
    return list_bank_transactions(db, tenant_id, bank_account_id=bank_account_id)


@router.post("/bank-transactions/{transaction_id}/match", response_model=BankTransactionResponse)
def api_match_bank_transaction(
    transaction_id: UUID,
    payload: MatchTransactionRequest,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankTransaction:
    bt = match_bank_transaction(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        transaction_id=transaction_id,
        journal_entry_id=payload.journal_entry_id,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return bt


# ============================================================
# Bank Reconciliation
# ============================================================

@router.post("/reconciliations", response_model=ReconciliationResponse, status_code=201)
def api_create_reconciliation(
    payload: ReconciliationCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankReconciliation:
    recon = create_reconciliation(
        db, tenant_id=tenant_id,
        bank_account_id=payload.bank_account_id,
        statement_date=payload.statement_date,
        statement_balance=payload.statement_balance,
    )
    commit_financial(db)
    return recon


@router.get("/reconciliations", response_model=list[ReconciliationResponse])
def api_list_reconciliations(
    tenant_id: UUID = Depends(require_tenant),
    bank_account_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[BankReconciliation]:
    return list_reconciliations(db, tenant_id, bank_account_id=bank_account_id)


@router.post("/reconciliations/{reconciliation_id}/complete", response_model=ReconciliationResponse)
def api_complete_reconciliation(
    reconciliation_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BankReconciliation:
    recon = complete_reconciliation(
        db, tenant_id=tenant_id, user_id=request.state.user_id,
        reconciliation_id=reconciliation_id,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return recon


# ============================================================
# Financial Statements
# ============================================================

@router.get("/statements/profit-and-loss", response_model=ProfitAndLossResponse)
def api_profit_and_loss(
    tenant_id: UUID = Depends(require_tenant),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    return get_profit_and_loss(db, tenant_id, currency.upper())


@router.get("/statements/balance-sheet", response_model=BalanceSheetResponse)
def api_balance_sheet(
    tenant_id: UUID = Depends(require_tenant),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    return get_balance_sheet(db, tenant_id, currency.upper())


@router.get("/statements/ar-aging", response_model=AgingResponse)
def api_ar_aging(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return get_ar_aging(db, tenant_id)


@router.get("/statements/ap-aging", response_model=AgingResponse)
def api_ap_aging(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return get_ap_aging(db, tenant_id)


@router.get("/statements/cash-flow", response_model=CashFlowResponse)
def api_cash_flow(
    tenant_id: UUID = Depends(require_tenant),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    return get_cash_flow(db, tenant_id, currency.upper())


# ============================================================
# Ledger — Chart of Accounts
# ============================================================

@router.post("/ledger/accounts", response_model=LedgerAccountResponse, status_code=201)
def create_ledger_account(
    payload: LedgerAccountCreate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ledger_models.LedgerAccount:
    existing = db.scalar(
        select(ledger_models.LedgerAccount).where(
            ledger_models.LedgerAccount.tenant_id == tenant_id,
            ledger_models.LedgerAccount.account_code == payload.account_code,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="account code already exists")
    account = ledger_models.LedgerAccount(tenant_id=tenant_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/ledger/accounts", response_model=list[LedgerAccountResponse])
def list_ledger_accounts(
    tenant_id: UUID = Depends(require_tenant),
    active_only: bool = Query(default=False),
    account_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ledger_models.LedgerAccount]:
    query = (
        select(ledger_models.LedgerAccount)
        .where(ledger_models.LedgerAccount.tenant_id == tenant_id)
        .order_by(ledger_models.LedgerAccount.account_code)
    )
    if active_only:
        query = query.where(ledger_models.LedgerAccount.is_active.is_(True))
    if account_type:
        query = query.where(ledger_models.LedgerAccount.account_type == account_type.lower())
    return db.scalars(query).all()


@router.patch("/ledger/accounts/{account_id}", response_model=LedgerAccountResponse)
def update_ledger_account(
    account_id: UUID,
    payload: LedgerAccountUpdate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ledger_models.LedgerAccount:
    account = db.get(ledger_models.LedgerAccount, account_id)
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


# ============================================================
# Ledger — Journal Entries
# ============================================================

@router.post("/ledger/entries", response_model=LedgerEntryResponse, status_code=201)
def create_ledger_entry(
    payload: LedgerEntryCreate,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LedgerEntryResponse:
    entry = ledger_service.create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        entry_date=payload.entry_date,
        description=payload.description,
        lines=[line.model_dump() for line in payload.lines],
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        currency=payload.currency,
    )
    commit_financial(db)
    return _serialize_ledger_entry(db, entry)


@router.get("/ledger/entries", response_model=list[LedgerEntryResponse])
def list_ledger_entries(
    tenant_id: UUID = Depends(require_tenant),
    status: str | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LedgerEntryResponse]:
    from datetime import date as date_type

    query = (
        select(ledger_models.LedgerEntry)
        .where(ledger_models.LedgerEntry.tenant_id == tenant_id)
        .order_by(ledger_models.LedgerEntry.entry_date.desc(), ledger_models.LedgerEntry.id)
    )
    if status:
        query = query.where(ledger_models.LedgerEntry.status == status)
    if reference_type:
        query = query.where(ledger_models.LedgerEntry.reference_type == reference_type)
    if start_date:
        query = query.where(ledger_models.LedgerEntry.entry_date >= date_type.fromisoformat(start_date))
    if end_date:
        query = query.where(ledger_models.LedgerEntry.entry_date <= date_type.fromisoformat(end_date))
    entries = db.scalars(query).all()
    return [_serialize_ledger_entry(db, e) for e in entries]


@router.get("/ledger/entries/{entry_id}", response_model=LedgerEntryResponse)
def get_ledger_entry(
    entry_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> LedgerEntryResponse:
    entry = db.scalar(
        select(ledger_models.LedgerEntry).where(
            ledger_models.LedgerEntry.id == entry_id,
            ledger_models.LedgerEntry.tenant_id == tenant_id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="ledger entry not found")
    return _serialize_ledger_entry(db, entry)


@router.post("/ledger/entries/{entry_id}/post", response_model=LedgerEntryResponse)
def post_ledger_entry(
    entry_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LedgerEntryResponse:
    entry = ledger_service.post_entry(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        entry_id=entry_id,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_ledger_entry(db, entry)


@router.post("/ledger/entries/{entry_id}/reverse", response_model=LedgerEntryResponse)
def reverse_ledger_entry(
    entry_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    reason: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> LedgerEntryResponse:
    entry = ledger_service.reverse_entry(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        entry_id=entry_id,
        reason=reason,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_ledger_entry(db, entry)


# ============================================================
# Ledger — Account Balances
# ============================================================

@router.get("/ledger/balances")
def list_account_balances(
    tenant_id: UUID = Depends(require_tenant),
    period_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    return reports_service.get_account_balances(db, tenant_id, period_id=period_id)


# ============================================================
# Ledger — Trial Balance
# ============================================================

@router.get("/ledger/trial-balance", response_model=LedgerTrialBalanceResponse)
def ledger_trial_balance(
    tenant_id: UUID = Depends(require_tenant),
    period_id: UUID | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    from datetime import date as date_type

    as_of = date_type.fromisoformat(as_of_date) if as_of_date else None
    return reports_service.get_trial_balance(
        db, tenant_id, period_id=period_id, as_of_date=as_of, currency=currency.upper(),
    )


# ============================================================
# Ledger — Balance Sheet
# ============================================================

@router.get("/ledger/balance-sheet", response_model=LedgerBalanceSheetResponse)
def ledger_balance_sheet(
    tenant_id: UUID = Depends(require_tenant),
    as_of_date: str | None = Query(default=None),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    from datetime import date as date_type

    as_of = date_type.fromisoformat(as_of_date) if as_of_date else None
    return reports_service.get_balance_sheet(
        db, tenant_id, as_of_date=as_of, currency=currency.upper(),
    )


# ============================================================
# Ledger — Income Statement
# ============================================================

@router.get("/ledger/income-statement", response_model=LedgerIncomeStatementResponse)
def ledger_income_statement(
    tenant_id: UUID = Depends(require_tenant),
    period_id: UUID | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    from datetime import date as date_type

    sd = date_type.fromisoformat(start_date) if start_date else None
    ed = date_type.fromisoformat(end_date) if end_date else None
    return reports_service.get_income_statement(
        db, tenant_id, period_id=period_id, start_date=sd, end_date=ed, currency=currency.upper(),
    )


# ============================================================
# Ledger — Posting Rules
# ============================================================

@router.post("/ledger/posting-rules", response_model=PostingRuleResponse, status_code=201)
def create_posting_rule(
    payload: PostingRuleCreate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ledger_models.PostingRule:
    rule = ledger_models.PostingRule(tenant_id=tenant_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/ledger/posting-rules", response_model=list[PostingRuleResponse])
def list_posting_rules(
    tenant_id: UUID = Depends(require_tenant),
    event_type: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ledger_models.PostingRule]:
    query = (
        select(ledger_models.PostingRule)
        .where(ledger_models.PostingRule.tenant_id == tenant_id)
        .order_by(ledger_models.PostingRule.event_type, ledger_models.PostingRule.rule_name)
    )
    if event_type:
        query = query.where(ledger_models.PostingRule.event_type == event_type)
    if active_only:
        query = query.where(ledger_models.PostingRule.is_active.is_(True))
    return db.scalars(query).all()


# ============================================================
# Ledger — Fiscal Periods
# ============================================================

@router.post("/ledger/fiscal-periods", response_model=FiscalPeriodResponse, status_code=201)
def create_fiscal_period(
    payload: FiscalPeriodCreate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ledger_models.FiscalPeriod:
    existing = db.scalar(
        select(ledger_models.FiscalPeriod).where(
            ledger_models.FiscalPeriod.tenant_id == tenant_id,
            ledger_models.FiscalPeriod.period_name == payload.period_name,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="fiscal period name already exists")
    overlap = db.scalar(
        select(ledger_models.FiscalPeriod).where(
            ledger_models.FiscalPeriod.tenant_id == tenant_id,
            ledger_models.FiscalPeriod.start_date <= payload.end_date,
            ledger_models.FiscalPeriod.end_date >= payload.start_date,
        )
    )
    if overlap is not None:
        raise HTTPException(status_code=409, detail="fiscal period overlaps with existing period")
    period = ledger_models.FiscalPeriod(tenant_id=tenant_id, **payload.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.get("/ledger/fiscal-periods", response_model=list[FiscalPeriodResponse])
def list_fiscal_periods(
    tenant_id: UUID = Depends(require_tenant),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ledger_models.FiscalPeriod]:
    query = (
        select(ledger_models.FiscalPeriod)
        .where(ledger_models.FiscalPeriod.tenant_id == tenant_id)
        .order_by(ledger_models.FiscalPeriod.start_date.desc())
    )
    if status:
        query = query.where(ledger_models.FiscalPeriod.status == status.lower())
    return db.scalars(query).all()


@router.post("/ledger/fiscal-periods/{period_id}/close", response_model=FiscalPeriodResponse)
def close_fiscal_period(
    period_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ledger_models.FiscalPeriod:
    from datetime import UTC, datetime

    period = db.scalar(
        select(ledger_models.FiscalPeriod).where(
            ledger_models.FiscalPeriod.id == period_id,
            ledger_models.FiscalPeriod.tenant_id == tenant_id,
        ).with_for_update()
    )
    if period is None:
        raise HTTPException(status_code=404, detail="fiscal period not found")
    if period.status != "open":
        raise HTTPException(status_code=409, detail="only open periods can be closed")

    period.status = "closed"
    period.closed_by = request.state.user_id
    period.closed_at = datetime.now(UTC)
    db.commit()
    db.refresh(period)
    return period


# ============================================================
# Ledger — Process Event
# ============================================================

class ProcessEventRequest(BaseModel):
    event_type: str
    event_data: dict = {}


@router.post("/ledger/process-event", response_model=LedgerEntryResponse)
def process_business_event(
    payload: ProcessEventRequest,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LedgerEntryResponse:
    entry = ledger_service.process_event(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        event_type=payload.event_type,
        event_data=payload.event_data,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    if isinstance(entry, list):
        return _serialize_ledger_entry(db, entry[0])
    return _serialize_ledger_entry(db, entry)


# ============================================================
# Serializers
# ============================================================

def _serialize_entry(db: Session, entry: JournalEntry) -> JournalEntryResponse:
    lines = db.scalars(
        select(JournalLine)
        .where(JournalLine.journal_entry_id == entry.id)
        .order_by(JournalLine.line_number)
    ).all()
    return JournalEntryResponse(
        id=entry.id, tenant_id=entry.tenant_id, entry_number=entry.entry_number,
        accounting_date=entry.accounting_date, currency=entry.currency,
        description=entry.description, reference=entry.reference,
        status=entry.status,
        posted_at=entry.posted_at.isoformat() if entry.posted_at else None,
        lines=[
            JournalLineResponse(
                id=line.id, account_id=line.account_id, line_number=line.line_number,
                description=line.description, debit=line.debit, credit=line.credit,
            )
            for line in lines
        ],
    )


def _serialize_ledger_entry(db: Session, entry: "ledger_models.LedgerEntry") -> LedgerEntryResponse:
    lines = db.scalars(
        select(ledger_models.LedgerLine)
        .where(ledger_models.LedgerLine.ledger_entry_id == entry.id)
        .order_by(ledger_models.LedgerLine.line_number)
    ).all()
    return LedgerEntryResponse(
        id=entry.id, tenant_id=entry.tenant_id, entry_number=entry.entry_number,
        entry_date=entry.entry_date, description=entry.description,
        reference_type=entry.reference_type, reference_id=entry.reference_id,
        currency=entry.currency, status=entry.status,
        posted_by=entry.posted_by,
        posted_at=entry.posted_at.isoformat() if entry.posted_at else None,
        reversed_by_entry_id=entry.reversed_by_entry_id,
        period_id=entry.period_id,
        lines=[
            LedgerLineResponse(
                id=line.id, account_id=line.account_id, line_number=line.line_number,
                description=line.description, debit=line.debit, credit=line.credit,
            )
            for line in lines
        ],
    )


def _serialize_invoice(db: Session, inv: Invoice) -> InvoiceResponse:
    lines = db.scalars(
        select(InvoiceLine)
        .where(InvoiceLine.invoice_id == inv.id)
        .order_by(InvoiceLine.line_number)
    ).all()
    return InvoiceResponse(
        id=inv.id, tenant_id=inv.tenant_id, invoice_number=inv.invoice_number,
        customer_id=inv.customer_id, status=inv.status,
        issue_date=inv.issue_date, due_date=inv.due_date, currency=inv.currency,
        subtotal=inv.subtotal, tax_amount=inv.tax_amount,
        total_amount=inv.total_amount, paid_amount=inv.paid_amount,
        balance_due=inv.balance_due, description=inv.description,
        notes=inv.notes, journal_entry_id=inv.journal_entry_id,
        created_by=inv.created_by,
        lines=[
            InvoiceLineResponse(
                id=line.id, line_number=line.line_number, description=line.description,
                quantity=line.quantity, unit_price=line.unit_price,
                tax_rate=line.tax_rate, account_id=line.account_id,
                line_total=line.line_total,
            )
            for line in lines
        ],
    )


def _serialize_bill(db: Session, bill: Bill) -> BillResponse:
    lines = db.scalars(
        select(BillLine)
        .where(BillLine.bill_id == bill.id)
        .order_by(BillLine.line_number)
    ).all()
    return BillResponse(
        id=bill.id, tenant_id=bill.tenant_id, bill_number=bill.bill_number,
        supplier_id=bill.supplier_id, status=bill.status,
        issue_date=bill.issue_date, due_date=bill.due_date, currency=bill.currency,
        subtotal=bill.subtotal, tax_amount=bill.tax_amount,
        total_amount=bill.total_amount, paid_amount=bill.paid_amount,
        balance_due=bill.balance_due, description=bill.description,
        notes=bill.notes, journal_entry_id=bill.journal_entry_id,
        created_by=bill.created_by,
        lines=[
            BillLineResponse(
                id=line.id, line_number=line.line_number, description=line.description,
                quantity=line.quantity, unit_price=line.unit_price,
                tax_rate=line.tax_rate, account_id=line.account_id,
                line_total=line.line_total,
            )
            for line in lines
        ],
    )


# ---------------------------------------------------------------------------
# Multi-Currency endpoints
# ---------------------------------------------------------------------------


class CurrencyConversionRequest(BaseModel):
    amount: Decimal
    from_currency: str = PydanticField(min_length=3, max_length=3)
    to_currency: str = PydanticField(min_length=3, max_length=3)


class ExchangeRateCreateRequest(BaseModel):
    from_currency: str = PydanticField(min_length=3, max_length=3)
    to_currency: str = PydanticField(min_length=3, max_length=3)
    rate: Decimal
    rate_date: str
    source: str | None = None


@router.post("/currency/convert")
def convert_currency_endpoint(
    payload: CurrencyConversionRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.convert_currency(
        db, tenant_id, payload.amount, payload.from_currency, payload.to_currency
    )


@router.get("/currency/exchange-rates")
def list_exchange_rates(
    from_currency: str | None = Query(None, min_length=3, max_length=3),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    from .models import CurrencyExchangeRate
    q = select(CurrencyExchangeRate).where(
        CurrencyExchangeRate.tenant_id == tenant_id,
        CurrencyExchangeRate.is_active.is_(True),
    )
    if from_currency:
        q = q.where(CurrencyExchangeRate.from_currency == from_currency.upper())
    rates = db.scalars(q.order_by(CurrencyExchangeRate.rate_date.desc()).limit(100)).all()
    return [
        {
            "id": r.id,
            "from_currency": r.from_currency,
            "to_currency": r.to_currency,
            "rate": r.rate,
            "rate_date": r.rate_date,
            "source": r.source,
        }
        for r in rates
    ]


@router.post("/currency/exchange-rates", status_code=201)
def create_exchange_rate(
    payload: ExchangeRateCreateRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
    from .models import CurrencyExchangeRate

    rate = CurrencyExchangeRate(
        tenant_id=tenant_id,
        from_currency=payload.from_currency.upper(),
        to_currency=payload.to_currency.upper(),
        rate=payload.rate,
        rate_date=date_type.fromisoformat(payload.rate_date),
        source=payload.source,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return {"id": rate.id, "status": "created"}


@router.get("/currency/summary")
def multi_currency_summary(
    base_currency: str = Query(default="USD", min_length=3, max_length=3),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_multi_currency_summary(db, tenant_id, base_currency)
