"""STEP 2 Slice 5 evidence: Document -> Ledger bridge, real DB round-trip.

Proves (per Production Completion Standard):
- validated invoice document -> balanced draft journal entry (Debit == Credit)
- governed posting works and updates account balances
- idempotency: re-processing the same document never creates a second entry
- untrusted/garbage extracted_data is rejected by the classification gate
- audit events recorded for draft + post
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app.db import SessionLocal
from backend.app.documents.ledger_bridge import (
    AP_ACCOUNT_CODE,
    EXPENSE_ACCOUNT_CODE,
    TAX_INPUT_ACCOUNT_CODE,
    classify_invoice_for_ledger,
    create_journal_draft_from_document,
    post_document_journal,
)
from backend.app.documents.models import Document
from backend.app.financial.ledger import FiscalPeriod, LedgerAccount
from backend.app.audit.models import AuditEvent


@pytest.fixture()
def ctx():
    """Create an isolated tenant/user context directly in the test DB."""
    from backend.app.auth.models import Tenant, User, TenantMembership
    db = SessionLocal()
    tenant = Tenant(id=uuid.uuid4(), name=f"BridgeTenant-{uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), email=f"bridge-{uuid.uuid4().hex[:8]}@x.com",
                password_hash="x")
    db.add_all([tenant, user])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin"))
    today = date.today()
    period = FiscalPeriod(tenant_id=tenant.id, period_name=f"FY{today.year}",
                          start_date=today - timedelta(days=180),
                          end_date=today + timedelta(days=180), status="open")
    accts = [
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
    db.add_all([period, *accts])
    db.flush()
    yield db, str(tenant.id), user.id
    db.rollback()
    db.close()


def _invoice_doc(db, tenant_id: str, data: dict) -> Document:
    doc = Document(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        filename="inv.pdf", original_filename="subcontractor-invoice.pdf",
        file_size=1234, mime_type="application/pdf",
        category="invoice", status="processed", extracted_data=data,
        storage_path=f"/tmp/{uuid.uuid4()}.pdf", checksum_sha256="0"*64,
    )
    db.add(doc)
    db.flush()
    return doc


def test_classification_gate_rejects_garbage(ctx):
    db, tid, uid = ctx
    doc = _invoice_doc(db, tid, {"total": "abc"})
    with pytest.raises(HTTPException) as exc:
        classify_invoice_for_ledger(doc)
    assert exc.value.status_code == 422
    doc2 = _invoice_doc(db, tid, {"total": "115.00", "subtotal": "100.00", "tax": "20.00"})
    with pytest.raises(HTTPException) as exc2:
        classify_invoice_for_ledger(doc2)  # math mismatch caught
    assert "line math mismatch" in exc2.value.detail


def test_draft_is_balanced_and_posting_updates_balances(ctx):
    db, tid, uid = ctx
    doc = _invoice_doc(db, tid, {
        "total": "11500.00", "subtotal": "10000.00", "tax": "1500.00",
        "currency": "EGP", "invoice_date": str(date.today()),
    })
    entry = create_journal_draft_from_document(
        db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    assert entry.status == "draft"
    assert entry.currency == "EGP"
    from backend.app.financial.ledger import LedgerLine, AccountBalance
    lines = db.query(LedgerLine).filter_by(ledger_entry_id=entry.id).all()
    debit = sum(l.debit for l in lines)
    credit = sum(l.credit for l in lines)
    assert debit == credit == Decimal("11500.000000")  # Debit == Credit invariant

    posted = post_document_journal(
        db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    assert posted.status == "posted"
    balances = db.query(AccountBalance).filter_by(tenant_id=uuid.UUID(tid)).all()
    total_dr = sum(b.debit_total for b in balances)
    total_cr = sum(b.credit_total for b in balances)
    assert total_dr == total_cr == Decimal("11500.000000")  # balanced posting recorded


def test_idempotency_no_duplicate_entry(ctx):
    db, tid, uid = ctx
    doc = _invoice_doc(db, tid, {"total": "500.00", "tax": "0", "currency": "USD"})
    e1 = create_journal_draft_from_document(
        db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    e2 = create_journal_draft_from_document(
        db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    assert e1.id == e2.id
    p1 = post_document_journal(db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    p2 = post_document_journal(db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    assert p1.id == p2.id and p2.status == "posted"
    from backend.app.financial.ledger import LedgerEntry
    per_doc = db.query(LedgerEntry).filter_by(reference_id=uuid.UUID(doc.id)).count()
    assert per_doc == 1  # never a second journal entry for the same document


def test_audit_trail_written(ctx):
    db, tid, uid = ctx
    doc = _invoice_doc(db, tid, {"total": "990.00", "subtotal": "900.00", "tax": "90.00"})
    post_document_journal(db, tenant_id=uuid.UUID(tid), user_id=uid, document_id=doc.id)
    actions = [e.action for e in db.query(AuditEvent).filter_by(
        tenant_id=uuid.UUID(tid), resource_id=uuid.UUID(doc.id)).all()]
    assert "documents.ledger.draft_created" in actions
    assert "documents.ledger.entry_posted" in actions
    assert any(a.startswith("financial.ledger") for a in
               [e.action for e in db.query(AuditEvent).filter_by(tenant_id=uuid.UUID(tid)).all()])
