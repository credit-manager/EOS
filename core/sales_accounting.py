"""Accounting integration for the transactional Sales cycle.

Keeps commercial sales documents and the general ledger in one transaction.
The helper intentionally creates a small, deterministic default chart for a
company when no dedicated accounts have been configured yet.
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.accounting_engine import AccountingEngine

DEFAULT_ACCOUNTS = {
    "1100": ("Cash", "asset"),
    "1200": ("Accounts Receivable", "asset"),
    "2100": ("Sales Tax Payable", "liability"),
    "4000": ("Sales Revenue", "revenue"),
}


def ensure_default_accounts(db: Session, tenant_id: str, company_id: str) -> dict[str, str]:
    accounting = AccountingEngine(db)
    result: dict[str, str] = {}
    for code, (name, account_type) in DEFAULT_ACCOUNTS.items():
        row = db.execute(text("SELECT id FROM dbp_accounts WHERE tenant_id = :tid AND company_id = :cid AND code = :code"), {"tid": tenant_id, "cid": company_id, "code": code}).fetchone()
        if row:
            result[code] = row[0]
            continue
        account_id = accounting.create_account(tenant_id, company_id, code, name, account_type)
        if not account_id:
            raise ValueError(f"Unable to provision accounting account {code}")
        result[code] = account_id
    return result


def _post_entry(db: Session, tenant_id: str, company_id: str, entry_date: str, description: str, reference: str, lines: list[tuple[str, Decimal, Decimal]], created_by: str) -> str:
    accounts = ensure_default_accounts(db, tenant_id, company_id)
    journal = AccountingEngine(db)
    entry_id = journal.create_journal_entry(tenant_id, company_id, entry_date, "standard", description=description, reference=reference, created_by=created_by)
    if not entry_id:
        raise ValueError("Unable to create journal entry")
    for code, debit, credit in lines:
        if debit == 0 and credit == 0:
            continue
        if not journal.add_journal_line(entry_id, accounts[code], tenant_id, float(debit), float(credit), description):
            raise ValueError(f"Unable to add journal line for account {code}")
    posted = journal.post_journal_entry(entry_id, tenant_id)
    if not posted["success"]:
        raise ValueError(posted["error"])
    return entry_id


def issue_invoice(db: Session, tenant_id: str, company_id: str, invoice_id: str, created_by: str) -> dict:
    row = db.execute(text("SELECT invoice_date, total_amount, tax_amount, status FROM dbp_sales_invoices WHERE id = :iid AND tenant_id = :tid AND company_id = :cid FOR UPDATE"), {"iid": invoice_id, "tid": tenant_id, "cid": company_id}).fetchone()
    if not row:
        return {"success": False, "error": "Invoice not found"}
    if row[3] in {"issued", "partial", "paid"}:
        existing = db.execute(text("SELECT id FROM dbp_journal_entries WHERE tenant_id = :tid AND company_id = :cid AND reference = :ref LIMIT 1"), {"tid": tenant_id, "cid": company_id, "ref": f"invoice:{invoice_id}"}).fetchone()
        return {"success": True, "journal_entry_id": existing[0] if existing else None, "status": row[3], "idempotent": True}
    if row[3] == "cancelled":
        return {"success": False, "error": "Cannot issue a cancelled invoice"}
    subtotal = Decimal(str(row[1] or 0)); tax = Decimal(str(row[2] or 0))
    journal_id = _post_entry(db, tenant_id, company_id, str(row[0] or datetime.now(timezone.utc).date()), f"Invoice {invoice_id}", f"invoice:{invoice_id}", [("1200", subtotal + tax, Decimal("0")), ("4000", Decimal("0"), subtotal), ("2100", Decimal("0"), tax)], created_by)
    db.execute(text("UPDATE dbp_sales_invoices SET status = 'issued' WHERE id = :iid AND tenant_id = :tid AND company_id = :cid"), {"iid": invoice_id, "tid": tenant_id, "cid": company_id})
    db.flush()
    return {"success": True, "journal_entry_id": journal_id, "status": "issued", "idempotent": False}


def record_payment(db: Session, tenant_id: str, company_id: str, invoice_id: str, amount: Decimal, payment_date: str, created_by: str) -> dict:
    row = db.execute(text("SELECT invoice_number, total_amount, tax_amount, paid_amount, status FROM dbp_sales_invoices WHERE id = :iid AND tenant_id = :tid AND company_id = :cid FOR UPDATE"), {"iid": invoice_id, "tid": tenant_id, "cid": company_id}).fetchone()
    if not row:
        return {"success": False, "error": "Invoice not found"}
    if row[4] == "cancelled":
        return {"success": False, "error": "Cannot record payment on a cancelled invoice"}
    total = Decimal(str(row[1] or 0)) + Decimal(str(row[2] or 0)); paid = Decimal(str(row[3] or 0))
    if amount <= 0 or amount > total - paid:
        return {"success": False, "error": "Payment amount exceeds remaining invoice balance"}
    new_paid = paid + amount; reference = f"payment:{invoice_id}:{new_paid}"
    existing = db.execute(text("SELECT id FROM dbp_journal_entries WHERE tenant_id = :tid AND company_id = :cid AND reference = :ref LIMIT 1"), {"tid": tenant_id, "cid": company_id, "ref": reference}).fetchone()
    if existing:
        return {"success": True, "journal_entry_id": existing[0], "paid_amount": float(new_paid), "idempotent": True}
    journal_id = _post_entry(db, tenant_id, company_id, payment_date or str(datetime.now(timezone.utc).date()), f"Payment for invoice {row[0]}", reference, [("1100", amount, Decimal("0")), ("1200", Decimal("0"), amount)], created_by)
    status = "paid" if new_paid >= total else "partial"
    db.execute(text("UPDATE dbp_sales_invoices SET paid_amount = :paid, status = :status WHERE id = :iid AND tenant_id = :tid AND company_id = :cid"), {"paid": new_paid, "status": status, "iid": invoice_id, "tid": tenant_id, "cid": company_id})
    db.flush()
    return {"success": True, "journal_entry_id": journal_id, "paid_amount": float(new_paid), "status": status, "idempotent": False}
