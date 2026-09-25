"""Evidence tests for the Document -> Ledger bridge."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app.audit.models import AuditEvent
from backend.app.auth.models import Tenant, TenantMembership, User
from backend.app.db import SessionLocal
from backend.app.documents.ledger_bridge import (
    AP_ACCOUNT_CODE, EXPENSE_ACCOUNT_CODE, TAX_INPUT_ACCOUNT_CODE,
    classify_invoice_for_ledger, create_journal_draft_from_document,
    post_document_journal,
)
from backend.app.documents.models import Document
from backend.app.financial.ledger import (
    AccountBalance, FiscalPeriod, LedgerAccount, LedgerEntry, LedgerLine,
)


@pytest.fixture()
def ctx():
    db = SessionLocal()
    tenant = Tenant(id=uuid.uuid4(), name=f"BridgeTenant-{uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), email=f"bridge-{uuid.uuid4().hex[:8]}@x.com", password_hash="x")
    db.add_all([tenant, user])
    db.flush()

    today = date.today()
    period = FiscalPeriod(
        tenant_id=tenant.id,
        period_name=f"FY{today.year}-{uuid.uuid4().hex[:6]}",
        start_date=today - timedelta(days=180),
        end_date=today + timedelta(days=180),
        status="open",
    )
    accounts = [
        LedgerAccount(tenant_id=tenant.id, account_code=AP_ACCOUNT_CODE,
                      account_name="Accounts Payable", account_type="liability",
                      normal_balance="credit"),
        LedgerAccount(tenant_id=tenant.id, account_code=EXPENSE_ACCOUNT_CODE,
                      account_name="Subcontract Expense", account_type="expense",
                      normal_balance="debit"),
        LedgerAccount(tenant_id=tenant.id, account_code=TAX_INPUT_ACCOUNT_CODE,
                      account_name="Input VAT", account_type="asset",
                      normal_balance="debit"),
    ]
    db.add_all([period, *accounts])
    db.flush()
    yield db, tenant.id, user.id
    db.rollback()
    db.close()


def _invoice_doc(db, tenant_id, data: dict) -> Document:
    document = Document(
        id=str(uuid.uuid4()), tenant_id=str(tenant_id),
        filename="inv.pdf", original_filename="subcontractor-invoice.pdf",
        file_size=1234, mime_type="application/pdf",
        category="invoice", status="processed", extracted_data=data,
        storage_path=f"/tmp/{uuid.uuid4()}.pdf", checksum_sha256="0" * 64,
    )
    db.add(document)
    db.flush()
    return document


def test_classification_gate_rejects_garbage(ctx):
    db, tenant_id, user_id = ctx
    document = _invoice_doc(db, tenant_id, {"total": "abc"})
    with pytest.raises(HTTPException) as exc:
        classify_invoice_for_ledger(document)
    assert exc.value.status_code == 422

    mismatched = _invoice_doc(
        db, tenant_id, {"total": "115.00", "subtotal": "100.00", "tax": "20.00"}
    )
    with pytest.raises(HTTPException) as exc2:
        classify_invoice_for_ledger(mismatched)
    assert "line math mismatch" in exc2.value.detail


def test_draft_is_balanced_and_posting_updates_balances(ctx):
    db, tenant_id, user_id = ctx
    document = _invoice_doc(db, tenant_id, {
        "total": "11500.00", "subtotal": "10000.00", "tax": "1500.00",
        "currency": "EGP", "invoice_date": str(date.today()),
    })
    entry = create_journal_draft_from_document(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    assert entry.status == "draft"
    assert entry.currency == "EGP"

    lines = db.query(LedgerLine).filter_by(ledger_entry_id=entry.id).all()
    debit = sum(line.debit for line in lines)
    credit = sum(line.credit for line in lines)
    assert debit == credit == Decimal("11500.000000")

    posted = post_document_journal(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    assert posted.status == "posted"

    balances = db.query(AccountBalance).filter_by(tenant_id=tenant_id).all()
    total_dr = sum(balance.debit_total for balance in balances)
    total_cr = sum(balance.credit_total for balance in balances)
    assert total_dr == total_cr == Decimal("11500.000000")


def test_idempotency_no_duplicate_entry(ctx):
    db, tenant_id, user_id = ctx
    document = _invoice_doc(db, tenant_id, {
        "total": "500.00", "tax": "0", "currency": "USD"
    })
    first = create_journal_draft_from_document(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    second = create_journal_draft_from_document(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    assert first.id == second.id

    posted_first = post_document_journal(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    posted_second = post_document_journal(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    assert posted_first.id == posted_second.id
    assert posted_second.status == "posted"
    assert db.query(LedgerEntry).filter_by(
        reference_id=uuid.UUID(document.id)
    ).count() == 1


def test_audit_trail_written(ctx):
    db, tenant_id, user_id = ctx
    document = _invoice_doc(
        db, tenant_id, {"total": "990.00", "subtotal": "900.00", "tax": "90.00"}
    )
    post_document_journal(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document.id
    )
    actions = [
        event.action
        for event in db.query(AuditEvent).filter_by(
            tenant_id=tenant_id, resource_id=uuid.UUID(document.id)
        ).all()
    ]
    assert "documents.ledger.draft_created" in actions
    assert "documents.ledger.entry_posted" in actions
    assert "financial.ledger.entry.posted" in actions
