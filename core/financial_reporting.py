"""Tenant-safe financial statements and fiscal-period controls."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text


class FinancialReportingEngine:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _money(value) -> float:
        return float(Decimal(str(value or 0)))

    def _company_exists(self, tenant_id: str, company_id: str) -> bool:
        return bool(self.db.execute(text("SELECT 1 FROM dbp_companies WHERE id=:cid AND tenant_id=:tid"), {"cid": company_id, "tid": tenant_id}).fetchone())

    @staticmethod
    def _validate_dates(start_date: str, end_date: str) -> None:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        if start > end:
            raise ValueError("start_date must not be after end_date")

    def income_statement(self, tenant_id: str, company_id: str, start_date: str, end_date: str) -> dict:
        self._validate_dates(start_date, end_date)
        if not self._company_exists(tenant_id, company_id):
            raise LookupError("Company not found")
        rows = self.db.execute(text("""
            SELECT a.account_type,a.id,a.code,a.name_en,COALESCE(SUM(l.debit),0) AS debit,COALESCE(SUM(l.credit),0) AS credit
            FROM dbp_accounts a JOIN dbp_journal_lines l ON l.account_id=a.id JOIN dbp_journal_entries j ON j.id=l.journal_entry_id
            WHERE a.tenant_id=:tid AND a.company_id=:cid AND j.tenant_id=:tid AND j.company_id=:cid AND j.status='posted'
              AND j.entry_date BETWEEN :start_date AND :end_date AND a.account_type IN ('revenue','expense')
            GROUP BY a.account_type,a.id,a.code,a.name_en ORDER BY a.code
        """), {"tid": tenant_id, "cid": company_id, "start_date": start_date, "end_date": end_date}).fetchall()
        revenue, expenses = [], []
        for r in rows:
            debit, credit = self._money(r.debit), self._money(r.credit)
            amount = credit - debit if r.account_type == "revenue" else debit - credit
            item = {"account_id": r.id, "code": r.code, "name": r.name_en, "amount": amount}
            (revenue if r.account_type == "revenue" else expenses).append(item)
        total_revenue = sum(x["amount"] for x in revenue)
        total_expenses = sum(x["amount"] for x in expenses)
        return {"start_date": start_date, "end_date": end_date, "revenue": revenue, "expenses": expenses, "total_revenue": total_revenue, "total_expenses": total_expenses, "net_income": total_revenue - total_expenses}

    def balance_sheet(self, tenant_id: str, company_id: str, as_of: str) -> dict:
        date.fromisoformat(as_of)
        if not self._company_exists(tenant_id, company_id):
            raise LookupError("Company not found")
        rows = self.db.execute(text("""
            SELECT a.id,a.code,a.name_en,a.account_type,a.opening_balance,
                   COALESCE(SUM(l.debit),0) AS debit,COALESCE(SUM(l.credit),0) AS credit
            FROM dbp_accounts a
            LEFT JOIN dbp_journal_lines l ON l.account_id=a.id
            LEFT JOIN dbp_journal_entries j ON j.id=l.journal_entry_id
              AND j.tenant_id=:tid AND j.company_id=:cid AND j.status='posted' AND j.entry_date<=:as_of
            WHERE a.tenant_id=:tid AND a.company_id=:cid AND a.is_active=true AND a.account_type IN ('asset','liability','equity')
            GROUP BY a.id,a.code,a.name_en,a.account_type,a.opening_balance ORDER BY a.code
        """), {"tid": tenant_id, "cid": company_id, "as_of": as_of}).fetchall()
        sections = {"asset": [], "liability": [], "equity": []}
        for r in rows:
            debit, credit, opening = self._money(r.debit), self._money(r.credit), self._money(r.opening_balance)
            amount = opening + (debit - credit if r.account_type == "asset" else credit - debit)
            sections[r.account_type].append({"account_id": r.id, "code": r.code, "name": r.name_en, "amount": amount})
        totals = {k: sum(x["amount"] for x in v) for k, v in sections.items()}
        return {"as_of": as_of, "assets": sections["asset"], "liabilities": sections["liability"], "equity": sections["equity"], "total_assets": totals["asset"], "total_liabilities": totals["liability"], "total_equity": totals["equity"], "is_balanced": abs(totals["asset"] - totals["liability"] - totals["equity"]) < 0.001}

    def close_period(self, tenant_id: str, company_id: str, period_id: str, user_id: str | None = None) -> dict:
        row = self.db.execute(text("SELECT id,status FROM dbp_fiscal_periods WHERE id=:pid AND tenant_id=:tid AND company_id=:cid FOR UPDATE"), {"pid": period_id, "tid": tenant_id, "cid": company_id}).fetchone()
        if not row:
            raise LookupError("Fiscal period not found")
        if row.status != "open":
            raise ValueError(f"Fiscal period is already {row.status}")
        self.db.execute(text("UPDATE dbp_fiscal_periods SET status='closed',closed_at=NOW(),closed_by=:uid WHERE id=:pid AND tenant_id=:tid AND company_id=:cid"), {"uid": user_id, "pid": period_id, "tid": tenant_id, "cid": company_id})
        self.db.commit()
        return {"period_id": period_id, "status": "closed"}

    def create_period(self, tenant_id: str, company_id: str, period_code: str, start_date: str, end_date: str) -> str:
        self._validate_dates(start_date, end_date)
        if not self._company_exists(tenant_id, company_id):
            raise LookupError("Company not found")
        period_id = str(uuid.uuid4())
        self.db.execute(text("INSERT INTO dbp_fiscal_periods (id,tenant_id,company_id,period_code,start_date,end_date) VALUES (:id,:tid,:cid,:code,:start_date,:end_date)"), {"id": period_id, "tid": tenant_id, "cid": company_id, "code": period_code, "start_date": start_date, "end_date": end_date})
        self.db.commit()
        return period_id
