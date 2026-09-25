from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
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
    PaymentAllocation,
    Supplier,
)

_ZERO = Decimal("0.000000")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def _next_entry_number(db: Session, tenant_id: UUID) -> int:
    current = db.scalar(
        select(func.max(JournalEntry.entry_number)).where(JournalEntry.tenant_id == tenant_id)
    )
    return (current or 0) + 1


def _next_number(db: Session, tenant_id: UUID, prefix: str, model: type) -> str:
    count = db.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
    )
    return f"{prefix}-{(count or 0) + 1:06d}"


def _validate_lines(
    db: Session, payload: "JournalEntryCreate", tenant_id: UUID
) -> tuple[list[Account], Decimal]:
    from .schemas import JournalEntryCreate  # noqa: F811

    debit_total = _money(sum((line.debit for line in payload.lines), _ZERO))
    credit_total = _money(sum((line.credit for line in payload.lines), _ZERO))
    if debit_total != credit_total or debit_total <= 0:
        raise HTTPException(status_code=422, detail="journal entry must be balanced and greater than zero")

    account_ids = [line.account_id for line in payload.lines]
    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id, Account.id.in_(account_ids))
    ).all()
    account_map = {account.id: account for account in accounts}
    missing = [str(aid) for aid in account_ids if aid not in account_map]
    if missing:
        raise HTTPException(status_code=404, detail=f"account(s) not found: {', '.join(missing)}")
    inactive = [str(a.id) for a in accounts if not a.is_active]
    if inactive:
        raise HTTPException(status_code=409, detail=f"inactive account(s): {', '.join(inactive)}")
    wrong_currency = [str(a.id) for a in accounts if a.currency != payload.currency]
    if wrong_currency:
        raise HTTPException(status_code=422, detail="all accounts must use the journal currency")
    return [account_map[account_id] for account_id in account_ids], debit_total


def _validate_persisted_lines(
    db: Session, entry: JournalEntry, lines: list[JournalLine], tenant_id: UUID
) -> None:
    account_ids = [line.account_id for line in lines]
    accounts = db.scalars(
        select(Account)
        .where(Account.tenant_id == tenant_id, Account.id.in_(account_ids))
        .with_for_update()
    ).all()
    account_map = {a.id: a for a in accounts}
    if len(account_map) != len(set(account_ids)):
        raise HTTPException(status_code=409, detail="journal line references an invalid tenant account")
    inactive = [str(a.id) for a in accounts if not a.is_active]
    if inactive:
        raise HTTPException(status_code=409, detail=f"inactive account(s): {', '.join(inactive)}")
    wrong_currency = [str(a.id) for a in accounts if a.currency != entry.currency]
    if wrong_currency:
        raise HTTPException(status_code=422, detail="all journal accounts must use the journal currency")


# ============================================================
# Journal Entry (existing)
# ============================================================

def create_draft(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payload: "JournalEntryCreate",
    request_id: str | None,
) -> JournalEntry:
    from .schemas import JournalEntryCreate  # noqa: F811

    accounts, _ = _validate_lines(db, payload, tenant_id)
    entry = JournalEntry(
        tenant_id=tenant_id,
        entry_number=_next_entry_number(db, tenant_id),
        accounting_date=payload.accounting_date,
        currency=payload.currency,
        description=payload.description,
        reference=payload.reference,
        status="draft",
        created_by=user_id,
    )
    db.add(entry)
    db.flush()
    account_by_id = {account.id: account for account in accounts}
    for index, line in enumerate(payload.lines, start=1):
        account = account_by_id[line.account_id]
        db.add(
            JournalLine(
                journal_entry_id=entry.id,
                account_id=account.id,
                line_number=index,
                description=line.description,
                debit=_money(line.debit),
                credit=_money(line.credit),
            )
        )
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="financial.journal.created",
            resource_type="journal_entry",
            resource_id=entry.id,
            request_id=request_id,
            details={"entry_number": entry.entry_number, "status": "draft"},
        )
    )
    return entry


def post_entry(
    db: Session, *, tenant_id: UUID, user_id: UUID, entry_id: UUID, request_id: str | None
) -> JournalEntry:
    entry = db.scalar(
        select(JournalEntry)
        .where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
        .with_for_update()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="journal entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=409, detail="only draft journal entries can be posted")

    lines = db.scalars(
        select(JournalLine)
        .where(JournalLine.journal_entry_id == entry.id)
        .order_by(JournalLine.line_number)
    ).all()
    debit_total = _money(sum((line.debit for line in lines), _ZERO))
    credit_total = _money(sum((line.credit for line in lines), _ZERO))
    if len(lines) < 2 or debit_total != credit_total or debit_total <= 0:
        raise HTTPException(status_code=422, detail="journal entry is not balanced")
    _validate_persisted_lines(db, entry, lines, tenant_id)

    entry.status = "posted"
    entry.posted_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="financial.journal.posted",
            resource_type="journal_entry",
            resource_id=entry.id,
            request_id=request_id,
            details={
                "entry_number": entry.entry_number,
                "debit_total": str(debit_total),
                "currency": entry.currency,
            },
        )
    )
    db.flush()
    return entry


def commit_financial(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="financial write conflicted with another transaction") from exc


# ============================================================
# Customer CRUD (AR)
# ============================================================

def create_customer(db: Session, *, tenant_id: UUID, data: dict) -> Customer:
    existing = db.scalar(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.code == data["code"])
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="customer code already exists")
    customer = Customer(tenant_id=tenant_id, **data)
    db.add(customer)
    db.flush()
    return customer


def get_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> Customer:
    customer = db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


def list_customers(db: Session, tenant_id: UUID, active_only: bool = False) -> list[Customer]:
    q = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.code)
    if active_only:
        q = q.where(Customer.is_active.is_(True))
    return list(db.scalars(q).all())


def update_customer(db: Session, tenant_id: UUID, customer_id: UUID, data: dict) -> Customer:
    customer = get_customer(db, tenant_id, customer_id)
    for k, v in data.items():
        if v is not None:
            setattr(customer, k, v)
    db.flush()
    return customer


# ============================================================
# Supplier CRUD (AP)
# ============================================================

def create_supplier(db: Session, *, tenant_id: UUID, data: dict) -> Supplier:
    existing = db.scalar(
        select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.code == data["code"])
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="supplier code already exists")
    supplier = Supplier(tenant_id=tenant_id, **data)
    db.add(supplier)
    db.flush()
    return supplier


def get_supplier(db: Session, tenant_id: UUID, supplier_id: UUID) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier not found")
    return supplier


def list_suppliers(db: Session, tenant_id: UUID, active_only: bool = False) -> list[Supplier]:
    q = select(Supplier).where(Supplier.tenant_id == tenant_id).order_by(Supplier.code)
    if active_only:
        q = q.where(Supplier.is_active.is_(True))
    return list(db.scalars(q).all())


def update_supplier(db: Session, tenant_id: UUID, supplier_id: UUID, data: dict) -> Supplier:
    supplier = get_supplier(db, tenant_id, supplier_id)
    for k, v in data.items():
        if v is not None:
            setattr(supplier, k, v)
    db.flush()
    return supplier


# ============================================================
# Invoice CRUD (AR)
# ============================================================

def create_invoice(
    db: Session, *, tenant_id: UUID, user_id: UUID, data: dict, lines_data: list[dict]
) -> Invoice:
    customer = get_customer(db, tenant_id, data["customer_id"])
    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=_next_number(db, tenant_id, "INV", Invoice),
        customer_id=customer.id,
        status="draft",
        issue_date=data["issue_date"],
        due_date=data["due_date"],
        currency=data.get("currency", customer.currency),
        description=data.get("description"),
        notes=data.get("notes"),
        created_by=user_id,
    )
    db.add(invoice)
    db.flush()

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for idx, ld in enumerate(lines_data, 1):
        qty = Decimal(str(ld.get("quantity", 1)))
        price = Decimal(str(ld.get("unit_price", 0)))
        tax_rate = Decimal(str(ld.get("tax_rate", 0)))
        line_total = _money(qty * price)
        tax_amount = _money(line_total * tax_rate)
        subtotal += line_total
        tax_total += tax_amount
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                line_number=idx,
                description=ld["description"],
                quantity=qty,
                unit_price=price,
                tax_rate=tax_rate,
                account_id=ld.get("account_id"),
                line_total=line_total,
            )
        )
    invoice.subtotal = _money(subtotal)
    invoice.tax_amount = _money(tax_total)
    invoice.total_amount = _money(subtotal + tax_total)
    invoice.balance_due = invoice.total_amount
    db.flush()
    return invoice


def get_invoice(db: Session, tenant_id: UUID, invoice_id: UUID) -> Invoice:
    inv = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return inv


def list_invoices(
    db: Session, tenant_id: UUID, customer_id: UUID | None = None, status: str | None = None
) -> list[Invoice]:
    q = select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.issue_date.desc())
    if customer_id:
        q = q.where(Invoice.customer_id == customer_id)
    if status:
        q = q.where(Invoice.status == status)
    return list(db.scalars(q).all())


def update_invoice_status(db: Session, tenant_id: UUID, invoice_id: UUID, new_status: str) -> Invoice:
    inv = get_invoice(db, tenant_id, invoice_id)
    allowed = {"draft", "sent", "paid", "overdue", "cancelled"}
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"invalid status: {new_status}")
    inv.status = new_status
    db.flush()
    return inv


def post_invoice_to_ledger(
    db: Session, *, tenant_id: UUID, user_id: UUID, invoice_id: UUID, request_id: str | None
) -> Invoice:
    inv = get_invoice(db, tenant_id, invoice_id)
    if inv.status != "draft":
        raise HTTPException(status_code=409, detail="only draft invoices can be posted")
    if inv.journal_entry_id:
        raise HTTPException(status_code=409, detail="invoice already posted")

    customer = db.get(Customer, inv.customer_id)
    ar_account_id = customer.ar_account_id if customer else None
    if not ar_account_id:
        raise HTTPException(status_code=422, detail="customer has no AR account configured")

    revenue_account = db.scalar(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_type == "revenue",
            Account.currency == inv.currency,
            Account.is_active.is_(True),
        )
    )
    if revenue_account is None:
        raise HTTPException(status_code=422, detail="no active revenue account found")

    entry = JournalEntry(
        tenant_id=tenant_id,
        entry_number=_next_entry_number(db, tenant_id),
        accounting_date=inv.issue_date,
        currency=inv.currency,
        description=f"Invoice {inv.invoice_number}",
        reference=inv.invoice_number,
        status="posted",
        posted_at=datetime.now(UTC),
        created_by=user_id,
    )
    db.add(entry)
    db.flush()

    db.add(JournalLine(
        journal_entry_id=entry.id, account_id=ar_account_id,
        line_number=1, description=f"AR - {inv.invoice_number}",
        debit=inv.total_amount, credit=Decimal("0"),
    ))
    db.add(JournalLine(
        journal_entry_id=entry.id, account_id=revenue_account.id,
        line_number=2, description=f"Revenue - {inv.invoice_number}",
        debit=Decimal("0"), credit=inv.total_amount,
    ))
    db.flush()

    inv.journal_entry_id = entry.id
    inv.status = "sent"
    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=user_id,
        action="financial.invoice.posted",
        resource_type="invoice", resource_id=inv.id,
        request_id=request_id,
        details={"invoice_number": inv.invoice_number, "amount": str(inv.total_amount)},
    ))
    db.flush()
    return inv


# ============================================================
# Bill CRUD (AP)
# ============================================================

def create_bill(
    db: Session, *, tenant_id: UUID, user_id: UUID, data: dict, lines_data: list[dict]
) -> Bill:
    supplier = get_supplier(db, tenant_id, data["supplier_id"])
    bill = Bill(
        tenant_id=tenant_id,
        bill_number=_next_number(db, tenant_id, "BILL", Bill),
        supplier_id=supplier.id,
        status="draft",
        issue_date=data["issue_date"],
        due_date=data["due_date"],
        currency=data.get("currency", supplier.currency),
        description=data.get("description"),
        notes=data.get("notes"),
        created_by=user_id,
    )
    db.add(bill)
    db.flush()

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for idx, ld in enumerate(lines_data, 1):
        qty = Decimal(str(ld.get("quantity", 1)))
        price = Decimal(str(ld.get("unit_price", 0)))
        tax_rate = Decimal(str(ld.get("tax_rate", 0)))
        line_total = _money(qty * price)
        tax_amount = _money(line_total * tax_rate)
        subtotal += line_total
        tax_total += tax_amount
        db.add(
            BillLine(
                bill_id=bill.id,
                line_number=idx,
                description=ld["description"],
                quantity=qty,
                unit_price=price,
                tax_rate=tax_rate,
                account_id=ld.get("account_id"),
                line_total=line_total,
            )
        )
    bill.subtotal = _money(subtotal)
    bill.tax_amount = _money(tax_total)
    bill.total_amount = _money(subtotal + tax_total)
    bill.balance_due = bill.total_amount
    db.flush()
    return bill


def get_bill(db: Session, tenant_id: UUID, bill_id: UUID) -> Bill:
    bill = db.scalar(
        select(Bill).where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    if bill is None:
        raise HTTPException(status_code=404, detail="bill not found")
    return bill


def list_bills(
    db: Session, tenant_id: UUID, supplier_id: UUID | None = None, status: str | None = None
) -> list[Bill]:
    q = select(Bill).where(Bill.tenant_id == tenant_id).order_by(Bill.issue_date.desc())
    if supplier_id:
        q = q.where(Bill.supplier_id == supplier_id)
    if status:
        q = q.where(Bill.status == status)
    return list(db.scalars(q).all())


def update_bill_status(db: Session, tenant_id: UUID, bill_id: UUID, new_status: str) -> Bill:
    bill = get_bill(db, tenant_id, bill_id)
    allowed = {"draft", "received", "approved", "paid", "overdue", "cancelled"}
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"invalid status: {new_status}")
    bill.status = new_status
    db.flush()
    return bill


def post_bill_to_ledger(
    db: Session, *, tenant_id: UUID, user_id: UUID, bill_id: UUID, request_id: str | None
) -> Bill:
    bill = get_bill(db, tenant_id, bill_id)
    if bill.status != "draft":
        raise HTTPException(status_code=409, detail="only draft bills can be posted")
    if bill.journal_entry_id:
        raise HTTPException(status_code=409, detail="bill already posted")

    supplier_obj = db.get(Supplier, bill.supplier_id)
    ap_account_id = supplier_obj.ap_account_id if supplier_obj else None
    if not ap_account_id:
        raise HTTPException(status_code=422, detail="supplier has no AP account configured")

    expense_account = db.scalar(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_type == "expense",
            Account.currency == bill.currency,
            Account.is_active.is_(True),
        )
    )
    if expense_account is None:
        raise HTTPException(status_code=422, detail="no active expense account found")

    entry = JournalEntry(
        tenant_id=tenant_id,
        entry_number=_next_entry_number(db, tenant_id),
        accounting_date=bill.issue_date,
        currency=bill.currency,
        description=f"Bill {bill.bill_number}",
        reference=bill.bill_number,
        status="posted",
        posted_at=datetime.now(UTC),
        created_by=user_id,
    )
    db.add(entry)
    db.flush()

    db.add(JournalLine(
        journal_entry_id=entry.id, account_id=expense_account.id,
        line_number=1, description=f"Expense - {bill.bill_number}",
        debit=bill.total_amount, credit=Decimal("0"),
    ))
    db.add(JournalLine(
        journal_entry_id=entry.id, account_id=ap_account_id,
        line_number=2, description=f"AP - {bill.bill_number}",
        debit=Decimal("0"), credit=bill.total_amount,
    ))
    db.flush()

    bill.journal_entry_id = entry.id
    bill.status = "received"
    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=user_id,
        action="financial.bill.posted",
        resource_type="bill", resource_id=bill.id,
        request_id=request_id,
        details={"bill_number": bill.bill_number, "amount": str(bill.total_amount)},
    ))
    db.flush()
    return bill


# ============================================================
# Payment (AR & AP)
# ============================================================

def create_payment(
    db: Session, *, tenant_id: UUID, user_id: UUID, data: dict
) -> Payment:
    payment = Payment(
        tenant_id=tenant_id,
        payment_number=_next_number(db, tenant_id, "PAY", Payment),
        payment_type=data["payment_type"],
        customer_id=data.get("customer_id"),
        supplier_id=data.get("supplier_id"),
        status="pending",
        payment_date=data["payment_date"],
        currency=data.get("currency", "USD"),
        amount=_money(Decimal(str(data["amount"]))),
        payment_method=data.get("payment_method", "bank_transfer"),
        reference=data.get("reference"),
        bank_account_id=data.get("bank_account_id"),
        created_by=user_id,
    )
    db.add(payment)
    db.flush()
    return payment


def get_payment(db: Session, tenant_id: UUID, payment_id: UUID) -> Payment:
    p = db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.tenant_id == tenant_id)
    )
    if p is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return p


def list_payments(
    db: Session, tenant_id: UUID, payment_type: str | None = None, status: str | None = None
) -> list[Payment]:
    q = select(Payment).where(Payment.tenant_id == tenant_id).order_by(Payment.payment_date.desc())
    if payment_type:
        q = q.where(Payment.payment_type == payment_type)
    if status:
        q = q.where(Payment.status == status)
    return list(db.scalars(q).all())


def allocate_payment(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payment_id: UUID,
    allocations: list[dict],
    request_id: str | None,
) -> Payment:
    payment = get_payment(db, tenant_id, payment_id)
    if payment.status != "pending":
        raise HTTPException(status_code=409, detail="only pending payments can be allocated")

    total_allocated = Decimal("0")
    for alloc in allocations:
        amt = _money(Decimal(str(alloc["amount"])))
        total_allocated += amt
        db.add(PaymentAllocation(
            payment_id=payment.id,
            invoice_id=alloc.get("invoice_id"),
            bill_id=alloc.get("bill_id"),
            allocated_amount=amt,
        ))

    if total_allocated > payment.amount:
        raise HTTPException(status_code=422, detail="total allocation exceeds payment amount")

    payment.status = "completed"
    db.flush()

    for alloc in allocations:
        if alloc.get("invoice_id"):
            inv = db.get(Invoice, alloc["invoice_id"])
            if inv:
                inv.paid_amount = _money(inv.paid_amount + Decimal(str(alloc["amount"])))
                inv.balance_due = _money(inv.total_amount - inv.paid_amount)
                if inv.balance_due <= 0:
                    inv.status = "paid"
        if alloc.get("bill_id"):
            bill = db.get(Bill, alloc["bill_id"])
            if bill:
                bill.paid_amount = _money(bill.paid_amount + Decimal(str(alloc["amount"])))
                bill.balance_due = _money(bill.total_amount - bill.paid_amount)
                if bill.balance_due <= 0:
                    bill.status = "paid"

    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=user_id,
        action="financial.payment.allocated",
        resource_type="payment", resource_id=payment.id,
        request_id=request_id,
        details={"payment_number": payment.payment_number, "amount": str(payment.amount)},
    ))
    db.flush()
    return payment


# ============================================================
# Bank Account
# ============================================================

def create_bank_account(db: Session, *, tenant_id: UUID, data: dict) -> BankAccount:
    ba = BankAccount(tenant_id=tenant_id, **data)
    db.add(ba)
    db.flush()
    return ba


def get_bank_account(db: Session, tenant_id: UUID, bank_account_id: UUID) -> BankAccount:
    ba = db.scalar(
        select(BankAccount).where(
            BankAccount.id == bank_account_id, BankAccount.tenant_id == tenant_id
        )
    )
    if ba is None:
        raise HTTPException(status_code=404, detail="bank account not found")
    return ba


def list_bank_accounts(db: Session, tenant_id: UUID) -> list[BankAccount]:
    return list(
        db.scalars(
            select(BankAccount).where(BankAccount.tenant_id == tenant_id).order_by(BankAccount.account_name)
        ).all()
    )


# ============================================================
# Bank Transaction
# ============================================================

def create_bank_transaction(db: Session, *, tenant_id: UUID, data: dict) -> BankTransaction:
    bt = BankTransaction(tenant_id=tenant_id, **data)
    db.add(bt)
    db.flush()
    return bt


def list_bank_transactions(
    db: Session, tenant_id: UUID, bank_account_id: UUID | None = None
) -> list[BankTransaction]:
    q = select(BankTransaction).where(BankTransaction.tenant_id == tenant_id).order_by(
        BankTransaction.transaction_date.desc()
    )
    if bank_account_id:
        q = q.where(BankTransaction.bank_account_id == bank_account_id)
    return list(db.scalars(q).all())


def match_bank_transaction(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    transaction_id: UUID,
    journal_entry_id: UUID | None = None,
    request_id: str | None,
) -> BankTransaction:
    bt = db.scalar(
        select(BankTransaction).where(
            BankTransaction.id == transaction_id, BankTransaction.tenant_id == tenant_id
        )
    )
    if bt is None:
        raise HTTPException(status_code=404, detail="bank transaction not found")
    bt.status = "matched"
    bt.matched_journal_entry_id = journal_entry_id
    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=user_id,
        action="financial.bank_transaction.matched",
        resource_type="bank_transaction", resource_id=bt.id,
        request_id=request_id,
        details={"description": bt.description},
    ))
    db.flush()
    return bt


# ============================================================
# Bank Reconciliation
# ============================================================

def create_reconciliation(
    db: Session, *, tenant_id: UUID, bank_account_id: UUID, statement_date: date, statement_balance: Decimal
) -> BankReconciliation:
    ba = get_bank_account(db, tenant_id, bank_account_id)
    book_balance = ba.current_balance
    difference = _money(Decimal(str(statement_balance)) - book_balance)
    recon = BankReconciliation(
        tenant_id=tenant_id,
        bank_account_id=bank_account_id,
        statement_date=statement_date,
        statement_balance=_money(Decimal(str(statement_balance))),
        book_balance=book_balance,
        difference=difference,
        status="draft",
    )
    db.add(recon)
    db.flush()
    return recon


def complete_reconciliation(
    db: Session, *, tenant_id: UUID, user_id: UUID, reconciliation_id: UUID, request_id: str | None
) -> BankReconciliation:
    recon = db.scalar(
        select(BankReconciliation).where(
            BankReconciliation.id == reconciliation_id,
            BankReconciliation.tenant_id == tenant_id,
        )
    )
    if recon is None:
        raise HTTPException(status_code=404, detail="reconciliation not found")
    if recon.status != "draft":
        raise HTTPException(status_code=409, detail="reconciliation already completed")

    unmatched = db.scalar(
        select(func.count())
        .select_from(BankTransaction)
        .where(
            BankTransaction.bank_account_id == recon.bank_account_id,
            BankTransaction.transaction_date <= recon.statement_date,
            BankTransaction.status == "pending",
        )
    )
    if unmatched and unmatched > 0:
        raise HTTPException(
            status_code=409,
            detail=f"{unmatched} transaction(s) still unmatched",
        )

    ba = db.get(BankAccount, recon.bank_account_id)
    ba.last_reconciled_date = recon.statement_date
    ba.last_reconciled_balance = recon.statement_balance

    recon.status = "completed"
    recon.reconciled_by = user_id
    recon.reconciled_at = datetime.now(UTC)
    db.add(AuditEvent(
        tenant_id=tenant_id, actor_id=user_id,
        action="financial.reconciliation.completed",
        resource_type="bank_reconciliation", resource_id=recon.id,
        request_id=request_id,
        details={"difference": str(recon.difference)},
    ))
    db.flush()
    return recon


def list_reconciliations(
    db: Session, tenant_id: UUID, bank_account_id: UUID | None = None
) -> list[BankReconciliation]:
    q = select(BankReconciliation).where(BankReconciliation.tenant_id == tenant_id).order_by(
        BankReconciliation.statement_date.desc()
    )
    if bank_account_id:
        q = q.where(BankReconciliation.bank_account_id == bank_account_id)
    return list(db.scalars(q).all())


# ============================================================
# Financial Statements
# ============================================================

def get_profit_and_loss(
    db: Session, tenant_id: UUID, currency: str = "USD"
) -> dict:
    """Generate Profit & Loss statement from posted journal entries."""
    rows = db.execute(
        select(
            Account.account_type,
            Account.code,
            Account.name,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            Account.tenant_id == tenant_id,
            Account.currency == currency,
            Account.account_type.in_(["revenue", "expense"]),
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.currency == currency,
            JournalEntry.status == "posted",
        )
        .group_by(Account.account_type, Account.code, Account.name)
        .order_by(Account.account_type, Account.code)
    ).all()

    revenue_lines = []
    expense_lines = []
    total_revenue = Decimal("0")
    total_expense = Decimal("0")

    for account_type, code, name, debit, credit in rows:
        debit = Decimal(str(debit or 0))
        credit = Decimal(str(credit or 0))
        balance = credit - debit if account_type == "revenue" else debit - credit
        line = {"code": code, "name": name, "balance": _money(balance)}
        if account_type == "revenue":
            revenue_lines.append(line)
            total_revenue += balance
        else:
            expense_lines.append(line)
            total_expense += balance

    gross_profit = total_revenue - total_expense
    return {
        "currency": currency,
        "revenue": {"lines": revenue_lines, "total": _money(total_revenue)},
        "expense": {"lines": expense_lines, "total": _money(total_expense)},
        "gross_profit": _money(gross_profit),
        "net_income": _money(gross_profit),
    }


def get_balance_sheet(
    db: Session, tenant_id: UUID, currency: str = "USD"
) -> dict:
    """Generate Balance Sheet from posted journal entries."""
    rows = db.execute(
        select(
            Account.account_type,
            Account.code,
            Account.name,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            Account.tenant_id == tenant_id,
            Account.currency == currency,
            Account.account_type.in_(["asset", "liability", "equity"]),
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.currency == currency,
            JournalEntry.status == "posted",
        )
        .group_by(Account.account_type, Account.code, Account.name)
        .order_by(Account.account_type, Account.code)
    ).all()

    assets = []
    liabilities = []
    equity = []
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for account_type, code, name, debit, credit in rows:
        debit = Decimal(str(debit or 0))
        credit = Decimal(str(credit or 0))
        if account_type == "asset":
            balance = debit - credit
            total_assets += balance
            assets.append({"code": code, "name": name, "balance": _money(balance)})
        elif account_type == "liability":
            balance = credit - debit
            total_liabilities += balance
            liabilities.append({"code": code, "name": name, "balance": _money(balance)})
        elif account_type == "equity":
            balance = credit - debit
            total_equity += balance
            equity.append({"code": code, "name": name, "balance": _money(balance)})

    return {
        "currency": currency,
        "assets": {"lines": assets, "total": _money(total_assets)},
        "liabilities": {"lines": liabilities, "total": _money(total_liabilities)},
        "equity": {"lines": equity, "total": _money(total_equity)},
        "total_liabilities_and_equity": _money(total_liabilities + total_equity),
        "is_balanced": _money(total_assets) == _money(total_liabilities + total_equity),
    }


def get_ar_aging(
    db: Session, tenant_id: UUID, as_of: date | None = None
) -> dict:
    """AR Aging summary: current, 1-30, 31-60, 61-90, 90+ days."""
    if as_of is None:
        as_of = date.today()

    invoices = db.scalars(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(["sent", "overdue"]),
            Invoice.balance_due > 0,
        )
    ).all()

    buckets = {
        "current": Decimal("0"),
        "1_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "over_90": Decimal("0"),
    }
    total = Decimal("0")

    for inv in invoices:
        days = (as_of - inv.due_date).days
        amt = inv.balance_due
        total += amt
        if days <= 0:
            buckets["current"] += amt
        elif days <= 30:
            buckets["1_30"] += amt
        elif days <= 60:
            buckets["31_60"] += amt
        elif days <= 90:
            buckets["61_90"] += amt
        else:
            buckets["over_90"] += amt

    return {
        "as_of": as_of.isoformat(),
        "buckets": {k: _money(v) for k, v in buckets.items()},
        "total_outstanding": _money(total),
    }


def get_ap_aging(
    db: Session, tenant_id: UUID, as_of: date | None = None
) -> dict:
    """AP Aging summary: current, 1-30, 31-60, 61-90, 90+ days."""
    if as_of is None:
        as_of = date.today()

    bills = db.scalars(
        select(Bill).where(
            Bill.tenant_id == tenant_id,
            Bill.status.in_(["received", "overdue"]),
            Bill.balance_due > 0,
        )
    ).all()

    buckets = {
        "current": Decimal("0"),
        "1_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "over_90": Decimal("0"),
    }
    total = Decimal("0")

    for bill in bills:
        days = (as_of - bill.due_date).days
        amt = bill.balance_due
        total += amt
        if days <= 0:
            buckets["current"] += amt
        elif days <= 30:
            buckets["1_30"] += amt
        elif days <= 60:
            buckets["31_60"] += amt
        elif days <= 90:
            buckets["61_90"] += amt
        else:
            buckets["over_90"] += amt

    return {
        "as_of": as_of.isoformat(),
        "buckets": {k: _money(v) for k, v in buckets.items()},
        "total_outstanding": _money(total),
    }


def get_cash_flow(
    db: Session, tenant_id: UUID, currency: str = "USD"
) -> dict:
    """Cash flow summary from bank transactions."""
    bank_accounts = db.scalars(
        select(BankAccount).where(BankAccount.tenant_id == tenant_id, BankAccount.currency == currency)
    ).all()

    total_inflow = Decimal("0")
    total_outflow = Decimal("0")
    accounts_summary = []

    for ba in bank_accounts:
        transactions = db.scalars(
            select(BankTransaction).where(BankTransaction.bank_account_id == ba.id)
        ).all()
        inflow = sum((t.credit for t in transactions), Decimal("0"))
        outflow = sum((t.debit for t in transactions), Decimal("0"))
        total_inflow += inflow
        total_outflow += outflow
        accounts_summary.append({
            "bank_account_id": ba.id,
            "account_name": ba.account_name,
            "current_balance": _money(ba.current_balance),
            "inflow": _money(inflow),
            "outflow": _money(outflow),
        })

    return {
        "currency": currency,
        "accounts": accounts_summary,
        "total_inflow": _money(total_inflow),
        "total_outflow": _money(total_outflow),
        "net_cash_flow": _money(total_inflow - total_outflow),
    }


# ---------------------------------------------------------------------------
# Multi-Currency Support
# ---------------------------------------------------------------------------

def get_exchange_rate(
    db: Session, tenant_id: UUID, from_currency: str, to_currency: str
) -> Decimal | None:
    """Get the latest exchange rate for a currency pair."""
    from .models import CurrencyExchangeRate

    if from_currency.upper() == to_currency.upper():
        return Decimal("1")

    rate = db.scalar(
        select(CurrencyExchangeRate).where(
            CurrencyExchangeRate.tenant_id == tenant_id,
            CurrencyExchangeRate.from_currency == from_currency.upper(),
            CurrencyExchangeRate.to_currency == to_currency.upper(),
            CurrencyExchangeRate.is_active.is_(True),
        ).order_by(CurrencyExchangeRate.rate_date.desc())
    )
    return rate.rate if rate else None


def convert_currency(
    db: Session, tenant_id: UUID, amount: Decimal, from_currency: str, to_currency: str
) -> dict:
    """Convert an amount between currencies."""
    rate = get_exchange_rate(db, tenant_id, from_currency, to_currency)
    if rate is None:
        raise HTTPException(
            status_code=400,
            detail=f"No exchange rate found for {from_currency} -> {to_currency}",
        )
    converted = _money(amount * rate)
    return {
        "original_amount": _money(amount),
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "rate": rate,
        "converted_amount": converted,
    }


def get_multi_currency_summary(
    db: Session, tenant_id: UUID, base_currency: str = "USD"
) -> dict:
    """Get financial summary with all currencies converted to base currency."""
    from .models import BankAccount, Invoice, Bill

    # Get all invoices grouped by currency
    invoice_currencies = db.scalars(
        select(Invoice.currency, func.count(), func.sum(Invoice.balance_due))
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(["sent", "overdue"]))
        .group_by(Invoice.currency)
    ).all()

    # Get all bills grouped by currency
    bill_currencies = db.scalars(
        select(Bill.currency, func.count(), func.sum(Bill.balance_due))
        .where(Bill.tenant_id == tenant_id, Bill.status.in_(["received", "approved", "overdue"]))
        .group_by(Bill.currency)
    ).all()

    # Get bank balances by currency
    bank_currencies = db.scalars(
        select(BankAccount.currency, func.count(), func.sum(BankAccount.current_balance))
        .where(BankAccount.tenant_id == tenant_id, BankAccount.is_active.is_(True))
        .group_by(BankAccount.currency)
    ).all()

    ar_by_currency = {}
    for currency, count, total in invoice_currencies:
        ar_by_currency[currency] = {"count": count, "balance": _money(total or Decimal("0"))}

    ap_by_currency = {}
    for currency, count, total in bill_currencies:
        ap_by_currency[currency] = {"count": count, "balance": _money(total or Decimal("0"))}

    bank_by_currency = {}
    for currency, count, total in bank_currencies:
        bank_by_currency[currency] = {"count": count, "balance": _money(total or Decimal("0"))}

    # Convert all to base currency
    total_ar_converted = Decimal("0")
    total_ap_converted = Decimal("0")
    total_bank_converted = Decimal("0")

    for currency, data in ar_by_currency.items():
        rate = get_exchange_rate(db, tenant_id, currency, base_currency)
        if rate:
            total_ar_converted += data["balance"] * rate

    for currency, data in ap_by_currency.items():
        rate = get_exchange_rate(db, tenant_id, currency, base_currency)
        if rate:
            total_ap_converted += data["balance"] * rate

    for currency, data in bank_by_currency.items():
        rate = get_exchange_rate(db, tenant_id, currency, base_currency)
        if rate:
            total_bank_converted += data["balance"] * rate

    return {
        "base_currency": base_currency,
        "ar_by_currency": ar_by_currency,
        "ap_by_currency": ap_by_currency,
        "bank_by_currency": bank_by_currency,
        "total_ar_converted": _money(total_ar_converted),
        "total_ap_converted": _money(total_ap_converted),
        "total_bank_converted": _money(total_bank_converted),
        "net_position_converted": _money(total_bank_converted - total_ap_converted),
    }
