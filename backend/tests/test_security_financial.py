"""S3/S7 financial security regression tests.

Proves construction financial postings go through Financial Core with:
- balanced, posted journal entries against validated tenant accounts,
- idempotent retry per business reference (no duplicate postings),
- missing-mapping rejection without partial state,
- cross-tenant denial at every link of the chain,
- inactive-account rejection without partial state.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app import db as db_module
from backend.app.construction import financial_integration as integration
from backend.app.construction import service as construction
from backend.app.construction.models import ProjectFinancialAccounts
from backend.app.financial.models import Account, JournalEntry, JournalLine
from backend.app.main import app

client = TestClient(app)
_TODAY = date(2026, 9, 12)


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"Tenant {email}",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return {
        "tenant_id": UUID(body["tenant_id"]),
        "user_id": UUID(body["user_id"]),
    }


def _make_account(db, tenant_id: UUID, code: str, account_type: str) -> Account:
    account = Account(
        tenant_id=tenant_id,
        code=code,
        name=code,
        account_type=account_type,
        currency="USD",
        is_active=True,
    )
    db.add(account)
    db.flush()
    return account


def _setup_chain(tag: str):
    """Build tenant + accounts + PFA + full procurement chain. Returns context dict."""
    identity = _register(f"s7-{tag}@example.com")
    tenant_id = identity["tenant_id"]
    user_id = identity["user_id"]
    db = db_module.SessionLocal()
    try:
        accounts = {
            "cash": _make_account(db, tenant_id, f"CASH-{tag}", "asset"),
            "ar": _make_account(db, tenant_id, f"AR-{tag}", "asset"),
            "ap": _make_account(db, tenant_id, f"AP-{tag}", "liability"),
            "inventory": _make_account(db, tenant_id, f"INV-{tag}", "asset"),
            "grni": _make_account(db, tenant_id, f"GRNI-{tag}", "liability"),
            "materials": _make_account(db, tenant_id, f"MAT-{tag}", "expense"),
            "revenue": _make_account(db, tenant_id, f"REV-{tag}", "revenue"),
            "labor": _make_account(db, tenant_id, f"LAB-{tag}", "expense"),
            "equipment": _make_account(db, tenant_id, f"EQP-{tag}", "expense"),
            "subcontractor": _make_account(db, tenant_id, f"SUB-{tag}", "expense"),
            "overhead": _make_account(db, tenant_id, f"OVH-{tag}", "expense"),
            "wip": _make_account(db, tenant_id, f"WIP-{tag}", "asset"),
        }
        project = construction.create_project(
            db, tenant_id=tenant_id, user_id=user_id,
            code=f"PRJ-{tag}", name=f"Project {tag}",
        )
        db.add(
            ProjectFinancialAccounts(
                tenant_id=tenant_id,
                project_id=project.id,
                cash_account_id=accounts["cash"].id,
                accounts_receivable_account_id=accounts["ar"].id,
                accounts_payable_account_id=accounts["ap"].id,
                inventory_account_id=accounts["inventory"].id,
                grni_account_id=accounts["grni"].id,
                materials_account_id=accounts["materials"].id,
                construction_revenue_account_id=accounts["revenue"].id,
                labor_account_id=accounts["labor"].id,
                equipment_account_id=accounts["equipment"].id,
                subcontractor_account_id=accounts["subcontractor"].id,
                overhead_account_id=accounts["overhead"].id,
                wip_account_id=accounts["wip"].id,
            )
        )
        contract = construction.create_contract(
            db, tenant_id=tenant_id, user_id=user_id, project_id=project.id,
            contract_number=f"CT-{tag}", title=f"Contract {tag}",
            counterparty="Client Co",
        )
        boq = construction.create_boq(
            db, tenant_id=tenant_id, user_id=user_id, contract_id=contract.id
        )
        boq_item = construction.add_boq_item(
            db, tenant_id=tenant_id, user_id=user_id, boq_id=boq.id,
            item_number=1, description="Concrete works", unit="m3",
            quantity=Decimal("10"), unit_rate=Decimal("100"),
            amount=Decimal("1000"),
        )
        claim = construction.create_progress_claim(
            db, tenant_id=tenant_id, user_id=user_id, contract_id=contract.id,
            claim_number=f"CLM-{tag}", claim_date=_TODAY,
            period_start=_TODAY, period_end=_TODAY,
        )
        construction.add_claim_line(
            db, tenant_id=tenant_id, user_id=user_id, claim_id=claim.id,
            boq_item_id=boq_item.id, description="Concrete works",
            quantity_completed=Decimal("5"), amount=Decimal("500"),
        )
        procurement = construction.create_procurement(
            db, tenant_id=tenant_id, user_id=user_id, project_id=project.id,
            requisition_number=f"REQ-{tag}", title=f"Procurement {tag}",
        )
        proc_line = construction.add_procurement_line(
            db, tenant_id=tenant_id, user_id=user_id,
            procurement_id=procurement.id, description="Cement",
            unit="bag", quantity=Decimal("100"),
            estimated_unit_price=Decimal("10"),
            estimated_total=Decimal("1000"),
        )
        purchase_order = construction.create_purchase_order(
            db, tenant_id=tenant_id, user_id=user_id,
            procurement_id=procurement.id, supplier_id=user_id,
            po_number=f"PO-{tag}",
        )
        po_line = construction.add_purchase_order_line(
            db, tenant_id=tenant_id, user_id=user_id, po_id=purchase_order.id,
            procurement_line_id=proc_line.id, description="Cement",
            unit="bag", quantity=Decimal("100"), unit_price=Decimal("10"),
            line_total=Decimal("1000"),
        )
        warehouse = construction.create_site_warehouse(
            db, tenant_id=tenant_id, user_id=user_id, project_id=project.id,
            code=f"WH-{tag}", name=f"Warehouse {tag}",
        )
        grn = construction.create_goods_receipt(
            db, tenant_id=tenant_id, user_id=user_id,
            purchase_order_id=purchase_order.id, grn_number=f"GRN-{tag}",
            received_date=_TODAY, warehouse_id=warehouse.id,
            received_by=user_id,
        )
        construction.add_goods_receipt_line(
            db, tenant_id=tenant_id, user_id=user_id, grn_id=grn.id,
            po_line_id=po_line.id, quantity_received=Decimal("100"),
            quantity_accepted=Decimal("100"),
        )
        invoice = construction.create_supplier_invoice(
            db, tenant_id=tenant_id, user_id=user_id,
            purchase_order_id=purchase_order.id, grn_id=grn.id,
            invoice_number=f"SINV-{tag}",
            supplier_invoice_number=f"SUP-{tag}",
            invoice_date=_TODAY, due_date=_TODAY,
        )
        construction.add_supplier_invoice_line(
            db, tenant_id=tenant_id, user_id=user_id, invoice_id=invoice.id,
            description="Cement", unit="bag", quantity=Decimal("100"),
            unit_price=Decimal("10"), line_total=Decimal("1000"),
        )
        payment = construction.create_payment(
            db, tenant_id=tenant_id, user_id=user_id,
            supplier_invoice_id=invoice.id, payment_number=f"PAY-{tag}",
            amount=Decimal("1000"), payment_date=_TODAY,
        )
        db.commit()
        db.refresh(claim)
        db.refresh(invoice)
        return {
            "db": db,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "accounts": accounts,
            "claim": claim,
            "invoice": invoice,
            "payment": payment,
            "grn": grn,
        }
    except Exception:
        db.close()
        raise


def _close(ctx) -> None:
    ctx["db"].close()


def _entry_totals(db, entry_id: UUID) -> tuple[Decimal, Decimal]:
    lines = db.scalars(
        select(JournalLine).where(JournalLine.journal_entry_id == entry_id)
    ).all()
    debit = sum((line.debit for line in lines), Decimal("0"))
    credit = sum((line.credit for line in lines), Decimal("0"))
    return debit, credit


def _count_entries(db, tenant_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.tenant_id == tenant_id)
        )
        or 0
    )


def test_claim_payment_posts_balanced_entry() -> None:
    ctx = _setup_chain("pay")
    db = ctx["db"]
    try:
        entry_id = integration.record_progress_claim_payment(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            claim=ctx["claim"], accounting_date=_TODAY, currency="USD",
        )
        entry = db.get(JournalEntry, entry_id)
        assert entry is not None
        assert entry.status == "posted"
        assert entry.reference == f"CLAIM-{ctx['claim'].claim_number}"
        debit, credit = _entry_totals(db, entry_id)
        assert debit == credit == Decimal("500")
    finally:
        _close(ctx)


def test_postings_are_idempotent_per_reference() -> None:
    ctx = _setup_chain("idem")
    db = ctx["db"]
    try:
        first = integration.record_supplier_invoice(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            invoice=ctx["invoice"], accounting_date=_TODAY, currency="USD",
        )
        before = _count_entries(db, ctx["tenant_id"])
        second = integration.record_supplier_invoice(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            invoice=ctx["invoice"], accounting_date=_TODAY, currency="USD",
        )
        assert second == first
        assert _count_entries(db, ctx["tenant_id"]) == before

        pay_first = integration.record_payment(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            payment=ctx["payment"], accounting_date=_TODAY, currency="USD",
        )
        pay_second = integration.record_payment(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            payment=ctx["payment"], accounting_date=_TODAY, currency="USD",
        )
        assert pay_second == pay_first

        grn_first = integration.record_goods_receipt(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            grn=ctx["grn"], accounting_date=_TODAY, currency="USD",
        )
        debit, credit = _entry_totals(db, grn_first)
        assert debit == credit == Decimal("1000")
        grn_second = integration.record_goods_receipt(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            grn=ctx["grn"], accounting_date=_TODAY, currency="USD",
        )
        assert grn_second == grn_first
    finally:
        _close(ctx)


def test_missing_account_mapping_rejected_without_posting() -> None:
    ctx = _setup_chain("nomap")
    db = ctx["db"]
    try:
        db.delete(
            db.scalar(
                select(ProjectFinancialAccounts).where(
                    ProjectFinancialAccounts.project_id
                    == construction.get_contract(
                        db,
                        tenant_id=ctx["tenant_id"],
                        contract_id=ctx["claim"].contract_id,
                    ).project_id
                )
            )
        )
        db.commit()
        before = _count_entries(db, ctx["tenant_id"])
        with pytest.raises(HTTPException) as exc_info:
            integration.record_progress_claim_payment(
                db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
                claim=ctx["claim"], accounting_date=_TODAY, currency="USD",
            )
        assert exc_info.value.status_code == 409
        assert _count_entries(db, ctx["tenant_id"]) == before
    finally:
        _close(ctx)


def test_cross_tenant_posting_is_denied() -> None:
    ctx = _setup_chain("xtenant")
    other = _register("s7-xtenant-other@example.com")
    db = ctx["db"]
    try:
        before = _count_entries(db, ctx["tenant_id"])
        with pytest.raises(HTTPException) as exc_info:
            integration.record_progress_claim_payment(
                db, tenant_id=other["tenant_id"], user_id=other["user_id"],
                claim=ctx["claim"], accounting_date=_TODAY, currency="USD",
            )
        assert exc_info.value.status_code == 404
        with pytest.raises(HTTPException):
            integration.record_supplier_invoice(
                db, tenant_id=other["tenant_id"], user_id=other["user_id"],
                invoice=ctx["invoice"], accounting_date=_TODAY, currency="USD",
            )
        assert _count_entries(db, ctx["tenant_id"]) == before
        assert _count_entries(db, other["tenant_id"]) == 0
    finally:
        _close(ctx)


def test_inactive_account_rejected_without_posting() -> None:
    ctx = _setup_chain("inactive")
    db = ctx["db"]
    try:
        ctx["accounts"]["cash"].is_active = False
        db.commit()
        before = _count_entries(db, ctx["tenant_id"])
        with pytest.raises(HTTPException) as exc_info:
            integration.record_payment(
                db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
                payment=ctx["payment"], accounting_date=_TODAY, currency="USD",
            )
        assert exc_info.value.status_code in (404, 409, 422)
        assert _count_entries(db, ctx["tenant_id"]) == before
    finally:
        _close(ctx)


def test_payment_posts_ap_to_cash() -> None:
    ctx = _setup_chain("apcash")
    db = ctx["db"]
    try:
        entry_id = integration.record_payment(
            db, tenant_id=ctx["tenant_id"], user_id=ctx["user_id"],
            payment=ctx["payment"], accounting_date=_TODAY, currency="USD",
        )
        lines = db.scalars(
            select(JournalLine)
            .where(JournalLine.journal_entry_id == entry_id)
            .order_by(JournalLine.line_number)
        ).all()
        assert len(lines) == 2
        assert lines[0].account_id == ctx["accounts"]["ap"].id
        assert lines[0].debit == Decimal("1000")
        assert lines[1].account_id == ctx["accounts"]["cash"].id
        assert lines[1].credit == Decimal("1000")
    finally:
        _close(ctx)
