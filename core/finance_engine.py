"""
P23 Finance & Treasury Engine — Bank Accounts, Payments, Exchange Rates, Budgets
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class FinanceEngine:
    """Finance & Treasury management."""

    PAYMENT_TYPES = {"receipt", "payment", "transfer", "refund"}
    PAYMENT_STATUSES = {"pending", "approved", "rejected", "completed", "cancelled"}

    def __init__(self, db: Session):
        self.db = db

    def _verify_company_tenant(self, company_id: str, tenant_id: str):
        """Raise 403 unless the company belongs to the calling tenant.

        P80.5D FIX: prevents a tenant from attaching records (bank accounts,
        payments, budgets) to a company owned by another tenant.
        """
        row = self.db.execute(text(
            "SELECT tenant_id FROM dbp_companies WHERE id = :cid"
        ), {"cid": company_id}).fetchone()
        if not row or row[0] != tenant_id:
            from fastapi import HTTPException
            raise HTTPException(403, detail="Company does not belong to your tenant")

    # ── BANK ACCOUNTS ──

    def create_bank_account(self, tenant_id: str, company_id: str, account_name: str, **kw) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        bid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_bank_accounts (id, tenant_id, company_id, account_name, "
            "bank_name, account_number, iban, currency_code, gl_account_id, current_balance) "
            "VALUES (:id, :tid, :cid, :an, :bn, :acc, :iban, :cc, :glid, :cb)"
        ), {"id": bid, "tid": tenant_id, "cid": company_id, "an": account_name,
            "bn": kw.get("bank_name"), "acc": kw.get("account_number"),
            "iban": kw.get("iban"), "cc": kw.get("currency_code", "SAR"),
            "glid": kw.get("gl_account_id"), "cb": kw.get("opening_balance", 0)})
        self.db.flush()
        return bid

    def get_bank_accounts(self, company_id: str, tenant_id: str) -> list[dict]:
        rows = self.db.execute(text(
            "SELECT id, account_name, bank_name, account_number, currency_code, "
            "current_balance, is_active FROM dbp_bank_accounts "
            "WHERE company_id = :cid AND tenant_id = :t ORDER BY account_name"
        ), {"cid": company_id, "t": tenant_id}).fetchall()
        return [{"id": r[0], "account_name": r[1], "bank_name": r[2],
                 "account_number": r[3], "currency_code": r[4],
                 "current_balance": float(r[5]) if r[5] else 0, "is_active": bool(r[6])}
                for r in rows]

    # ── PAYMENTS ──

    def create_payment(self, tenant_id: str, company_id: str, payment_type: str,
                       payment_date: str, amount: float, **kw) -> str | None:
        if payment_type not in self.PAYMENT_TYPES or amount <= 0:
            return None
        self._verify_company_tenant(company_id, tenant_id)
        baid = kw.get("bank_account_id")
        if baid:
            bank_row = self.db.execute(text(
                "SELECT tenant_id FROM dbp_bank_accounts WHERE id = :bid"
            ), {"bid": baid}).fetchone()
            if not bank_row or bank_row[0] != tenant_id:
                from fastapi import HTTPException
                raise HTTPException(403, detail="Bank account does not belong to your tenant")
        pid = str(uuid.uuid4())
        pnum = self._next_payment_number(company_id)
        self.db.execute(text(
            "INSERT INTO dbp_payments (id, tenant_id, company_id, payment_number, "
            "payment_type, payment_date, amount, currency_code, exchange_rate, "
            "bank_account_id, payee_name, payee_type, reference, description, "
            "cost_center_id, created_by) "
            "VALUES (:id, :tid, :cid, :pn, :pt, :pd, :amt, :cc, :er, :baid, "
            ":payee, :ptyp, :ref, :desc, :ccid, :cb)"
        ), {"id": pid, "tid": tenant_id, "cid": company_id, "pn": pnum,
            "pt": payment_type, "pd": payment_date, "amt": amount,
            "cc": kw.get("currency_code", "SAR"), "er": kw.get("exchange_rate", 1),
            "baid": kw.get("bank_account_id"), "payee": kw.get("payee_name"),
            "ptyp": kw.get("payee_type"), "ref": kw.get("reference"),
            "desc": kw.get("description"), "ccid": kw.get("cost_center_id"),
            "cb": kw.get("created_by")})
        self.db.flush()
        return pid

    def approve_payment(self, payment_id: str, approved_by: str, tenant_id: str) -> dict[str, Any]:
        # P80.5D FIX: scope the payment lookup AND the bank-account balance
        # mutation to the caller's tenant, so a tenant cannot approve another
        # tenant's payment and rewrite its cash balance.
        row = self.db.execute(text(
            "SELECT status, amount, payment_type, bank_account_id FROM dbp_payments "
            "WHERE id = :pid AND tenant_id = :t"
        ), {"pid": payment_id, "t": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Payment not found"}
        if row[0] != "pending":
            return {"success": False, "error": f"Cannot approve payment in '{row[0]}' status"}

        amount, ptype, bank_id = float(row[1]), row[2], row[3]

        if bank_id:
            bank_row = self.db.execute(text(
                "SELECT tenant_id FROM dbp_bank_accounts WHERE id = :bid"
            ), {"bid": bank_id}).fetchone()
            if not bank_row or bank_row[0] != tenant_id:
                return {"success": False, "error": "Bank account not found for tenant"}
            if ptype in ("receipt", "refund"):
                self.db.execute(text(
                    "UPDATE dbp_bank_accounts SET current_balance = current_balance + :amt "
                    "WHERE id = :bid AND tenant_id = :t"
                ), {"amt": amount, "bid": bank_id, "t": tenant_id})
            else:
                self.db.execute(text(
                    "UPDATE dbp_bank_accounts SET current_balance = current_balance - :amt "
                    "WHERE id = :bid AND tenant_id = :t"
                ), {"amt": amount, "bid": bank_id, "t": tenant_id})

        self.db.execute(text(
            "UPDATE dbp_payments SET status='completed', approved_by = :ab WHERE id = :pid AND tenant_id = :t"
        ), {"ab": approved_by, "pid": payment_id, "t": tenant_id})
        self.db.flush()
        return {"success": True, "status": "completed"}

    def list_payments(self, company_id: str, tenant_id: str, payment_type: str | None = None,
                      status: str | None = None, limit: int = 50) -> list[dict]:
        conditions = ["company_id = :cid", "tenant_id = :t"]
        params: dict[str, Any] = {"cid": company_id, "t": tenant_id, "lim": limit}
        if payment_type:
            conditions.append("payment_type = :pt")
            params["pt"] = payment_type
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)

        rows = self.db.execute(text(
            f"SELECT id, payment_number, payment_type, payment_date, amount, "
            f"currency_code, payee_name, status, created_at "
            f"FROM dbp_payments WHERE {where} ORDER BY payment_date DESC LIMIT :lim"
        ), params).fetchall()
        return [{"id": r[0], "payment_number": r[1], "payment_type": r[2],
                 "payment_date": str(r[3]) if r[3] else None,
                 "amount": float(r[4]) if r[4] else 0, "currency_code": r[5],
                 "payee_name": r[6], "status": r[7],
                 "created_at": r[8].isoformat() if r[8] else None} for r in rows]

    # ── EXCHANGE RATES ──

    def set_exchange_rate(self, from_currency: str, to_currency: str,
                          rate: float, rate_date: str, source: str | None = None) -> str:
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_exchange_rates (id, from_currency, to_currency, rate, rate_date, source) "
            "VALUES (:id, :fc, :tc, :rate, :rd, :src)"
        ), {"id": rid, "fc": from_currency, "tc": to_currency,
            "rate": rate, "rd": rate_date, "src": source})
        self.db.flush()
        return rid

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> dict | None:
        row = self.db.execute(text(
            "SELECT id, rate, rate_date, source FROM dbp_exchange_rates "
            "WHERE from_currency = :fc AND to_currency = :tc "
            "ORDER BY rate_date DESC LIMIT 1"
        ), {"fc": from_currency, "tc": to_currency}).fetchone()
        if not row:
            return None
        return {"id": row[0], "rate": float(row[1]), "rate_date": str(row[2]) if row[2] else None, "source": row[3]}

    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> dict | None:
        if from_currency == to_currency:
            return {"original": amount, "converted": amount, "rate": 1}
        rate_info = self.get_exchange_rate(from_currency, to_currency)
        if not rate_info:
            return None
        return {"original": amount, "converted": round(amount * rate_info["rate"], 2),
                "rate": rate_info["rate"], "rate_date": rate_info["rate_date"]}

    # ── BUDGETS ──

    def create_budget(self, tenant_id: str, company_id: str, account_id: str,
                      fiscal_year_id: str, budget_amount: float,
                      cost_center_id: str | None = None, period: str | None = None) -> str:
        self._verify_company_tenant(company_id, tenant_id)
        bid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_budgets (id, tenant_id, company_id, account_id, "
            "cost_center_id, fiscal_year_id, period, budget_amount) "
            "VALUES (:id, :tid, :cid, :aid, :ccid, :fyid, :per, :ba)"
        ), {"id": bid, "tid": tenant_id, "cid": company_id, "aid": account_id,
            "ccid": cost_center_id, "fyid": fiscal_year_id, "per": period, "ba": budget_amount})
        self.db.flush()
        return bid

    def get_budgets(self, company_id: str, tenant_id: str, fiscal_year_id: str | None = None) -> list[dict]:
        conditions = ["b.company_id = :cid", "b.tenant_id = :t"]
        params: dict[str, Any] = {"cid": company_id, "t": tenant_id}
        if fiscal_year_id:
            conditions.append("b.fiscal_year_id = :fyid")
            params["fyid"] = fiscal_year_id
        where = " AND ".join(conditions)

        rows = self.db.execute(text(
            f"SELECT b.id, b.account_id, a.code, a.name_en, b.cost_center_id, "
            f"b.period, b.budget_amount, b.actual_amount, b.variance "
            f"FROM dbp_budgets b LEFT JOIN dbp_accounts a ON b.account_id = a.id "
            f"WHERE {where} ORDER BY a.code"
        ), params).fetchall()
        return [{"id": r[0], "account_id": r[1], "account_code": r[2],
                 "account_name": r[3], "cost_center_id": r[4],
                 "period": r[5], "budget_amount": float(r[6]) if r[6] else 0,
                 "actual_amount": float(r[7]) if r[7] else 0,
                 "variance": float(r[8]) if r[8] else 0} for r in rows]

    def get_budget_utilization(self, company_id: str, tenant_id: str) -> list[dict]:
        budgets = self.get_budgets(company_id, tenant_id)
        result = []
        for b in budgets:
            pct = (b["actual_amount"] / b["budget_amount"] * 100) if b["budget_amount"] > 0 else 0
            result.append({**b, "utilization_pct": round(pct, 2),
                           "remaining": b["budget_amount"] - b["actual_amount"]})
        return result

    # ── HELPERS ──

    def _next_payment_number(self, company_id: str) -> str:
        last = self.db.execute(text(
            "SELECT payment_number FROM dbp_payments "
            "WHERE company_id = :cid ORDER BY created_at DESC LIMIT 1"
        ), {"cid": company_id}).fetchone()
        if last and last[0]:
            try:
                num = int(last[0].replace("PAY-", "")) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f"PAY-{num:06d}"
