"""EOS Advanced Reporting Engine.

Financial reports are derived from posted general-ledger entries whenever the
ledger is available, with tenant-scoped operational reports for commerce.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import text


class ReportingEngine:
    def __init__(self, db):
        self.db = db

    def _query(self, sql, params=None):
        rows = self.db.execute(text(sql), params or {}).fetchall()
        return [dict(r._mapping) for r in rows]

    def _scalar(self, sql, params=None):
        row = self.db.execute(text(sql), params or {}).fetchone()
        return row[0] if row else 0

    @staticmethod
    def _date_range(start_date=None, end_date=None, default_days=30):
        today = datetime.utcnow().date()
        start = start_date or str(today - timedelta(days=default_days))
        end = end_date or str(today)
        if str(start) > str(end):
            raise ValueError("start_date must not be after end_date")
        return str(start), str(end)

    def _posted_account_movements(self, tenant_id, start_date=None, end_date=None):
        sql = """
            SELECT LOWER(a.account_type) AS account_type,
                   COALESCE(SUM(jl.debit), 0) AS debit,
                   COALESCE(SUM(jl.credit), 0) AS credit
              FROM dbp_journal_entries je
              JOIN dbp_journal_lines jl ON jl.journal_entry_id = je.id
              JOIN dbp_accounts a ON a.id = jl.account_id AND a.tenant_id = je.tenant_id
             WHERE je.tenant_id = :tenant_id
               AND je.status = 'posted'
        """
        params = {"tenant_id": tenant_id}
        if start_date is not None:
            sql += " AND je.entry_date >= :start_date"
            params["start_date"] = start_date
        if end_date is not None:
            sql += " AND je.entry_date <= :end_date"
            params["end_date"] = end_date
        sql += " GROUP BY LOWER(a.account_type)"
        return self._query(sql, params)

    def profit_and_loss(self, tenant_id, start_date=None, end_date=None):
        start, end = self._date_range(start_date, end_date)
        rows = self._posted_account_movements(tenant_id, start, end)

        revenue = Decimal("0")
        cogs = Decimal("0")
        operating_expenses = Decimal("0")
        for row in rows:
            account_type = row.get("account_type") or ""
            debit = Decimal(str(row.get("debit") or 0))
            credit = Decimal(str(row.get("credit") or 0))
            if account_type in {"revenue", "income"}:
                revenue += credit - debit
            elif account_type in {"cost_of_goods", "cogs", "cost_of_sales"}:
                cogs += debit - credit
            elif account_type in {"expense", "expenses", "operating_expense"}:
                operating_expenses += debit - credit

        gross_profit = revenue - cogs
        net_income = gross_profit - operating_expenses
        gross_margin = (gross_profit / revenue * Decimal("100")) if revenue else Decimal("0")
        return {
            "period": {"start": start, "end": end},
            "revenue": float(revenue),
            "cost_of_goods": float(cogs),
            "gross_profit": float(gross_profit),
            "gross_margin": float(gross_margin),
            "operating_expenses": float(operating_expenses),
            "net_income": float(net_income),
        }

    def balance_sheet(self, tenant_id, as_of_date=None):
        as_of = as_of_date or str(datetime.utcnow().date())
        rows = self._query(
            """
            SELECT a.code, a.name_en, LOWER(a.account_type) AS account_type,
                   COALESCE(a.opening_balance,0) +
                   COALESCE(SUM(CASE WHEN je.status='posted' THEN jl.debit-jl.credit ELSE 0 END),0) AS net_balance
              FROM dbp_accounts a
              LEFT JOIN dbp_journal_lines jl ON jl.account_id = a.id
              LEFT JOIN dbp_journal_entries je
                     ON je.id = jl.journal_entry_id
                    AND je.tenant_id = a.tenant_id
                    AND je.entry_date <= :as_of
             WHERE a.tenant_id = :tenant_id
               AND a.is_active = true
             GROUP BY a.code, a.name_en, a.account_type, a.opening_balance
             ORDER BY a.code
            """,
            {"tenant_id": tenant_id, "as_of": as_of},
        )

        assets = Decimal("0")
        liabilities = Decimal("0")
        equity = Decimal("0")
        accounts = []
        for row in rows:
            net = Decimal(str(row.get("net_balance") or 0))
            account_type = row.get("account_type") or ""
            if account_type == "asset":
                presentation = net
                assets += net
            elif account_type in {"liability", "liabilities"}:
                presentation = -net
                liabilities += presentation
            elif account_type in {"equity", "capital"}:
                presentation = -net
                equity += presentation
            else:
                continue
            accounts.append({
                "code": row.get("code"),
                "name": row.get("name_en"),
                "account_type": account_type,
                "balance": float(presentation),
            })

        return {
            "as_of_date": as_of,
            "assets": {"total": float(assets)},
            "liabilities": {"total": float(liabilities)},
            "equity": {"total": float(equity)},
            "balance_check": float(assets - liabilities - equity),
            "accounts": accounts,
        }

    def cash_flow(self, tenant_id, days=30):
        try:
            days = int(days)
        except (TypeError, ValueError) as exc:
            raise ValueError("days must be an integer") from exc
        days = max(1, min(days, 3660))
        start = (datetime.utcnow() - timedelta(days=days)).date()
        inflows = self._scalar(
            """
            SELECT COALESCE(SUM(amount),0)
              FROM dbp_payment_transactions
             WHERE tenant_id=:t AND transaction_type='payment'
               AND status='completed' AND created_at::date >= :s
            """,
            {"t": tenant_id, "s": start},
        )
        outflows = self._scalar(
            """
            SELECT COALESCE(SUM(amount),0)
              FROM dbp_payment_transactions
             WHERE tenant_id=:t AND transaction_type='refund'
               AND status='completed' AND created_at::date >= :s
            """,
            {"t": tenant_id, "s": start},
        )
        inflows = Decimal(str(inflows or 0))
        outflows = Decimal(str(outflows or 0))
        return {
            "period_days": days,
            "inflows": float(inflows),
            "outflows": float(outflows),
            "net_cash_flow": float(inflows - outflows),
        }

    def sales_report(self, tenant_id, start_date=None, end_date=None):
        start, end = self._date_range(start_date, end_date)
        orders = self._query(
            """
            SELECT DATE(created_at) AS date, COUNT(*) AS count,
                   COALESCE(SUM(total),0) AS amount
              FROM dbp_trading_sales_orders
             WHERE tenant_id=:t AND created_at::date BETWEEN :s AND :e
             GROUP BY DATE(created_at) ORDER BY date
            """,
            {"t": tenant_id, "s": start, "e": end},
        )
        top_customers = self._query(
            """
            SELECT customer_id, COUNT(*) AS order_count,
                   COALESCE(SUM(total),0) AS total_amount
              FROM dbp_trading_sales_orders
             WHERE tenant_id=:t AND created_at::date BETWEEN :s AND :e
             GROUP BY customer_id ORDER BY total_amount DESC LIMIT 10
            """,
            {"t": tenant_id, "s": start, "e": end},
        )
        return {"period": {"start": start, "end": end}, "daily": orders, "top_customers": top_customers}

    def inventory_report(self, tenant_id):
        items = self._query(
            """
            SELECT ci.id, ci.name, cs.on_hand AS qty_on_hand, cs.unit_cost,
                   cs.on_hand * cs.unit_cost AS stock_value, cs.warehouse_id
              FROM dbp_commerce_items ci
              JOIN dbp_commerce_stock cs ON ci.id=cs.item_id AND ci.tenant_id=cs.tenant_id
             WHERE ci.tenant_id=:t ORDER BY stock_value DESC
            """,
            {"t": tenant_id},
        )
        total_value = sum((Decimal(str(i.get("stock_value") or 0)) for i in items), Decimal("0"))
        low_stock = [i for i in items if (i.get("qty_on_hand") or 0) <= 10]
        return {
            "total_items": len(items),
            "total_stock_value": float(total_value),
            "low_stock_items": len(low_stock),
            "items": items[:50],
        }

    def customer_aging(self, tenant_id):
        aging = {"current": Decimal("0"), "30_days": Decimal("0"), "60_days": Decimal("0"), "90_days": Decimal("0"), "over_90": Decimal("0")}
        rows = self._query(
            """
            SELECT balance AS total_amount,
                   CURRENT_DATE - due_date::date AS days_overdue
              FROM dbp_trading_sales_invoices
             WHERE tenant_id=:t AND status != 'paid'
            """,
            {"t": tenant_id},
        )
        for row in rows:
            days = int(row.get("days_overdue", 0) or 0)
            amount = Decimal(str(row.get("total_amount") or 0))
            if days <= 0:
                aging["current"] += amount
            elif days <= 30:
                aging["30_days"] += amount
            elif days <= 60:
                aging["60_days"] += amount
            elif days <= 90:
                aging["90_days"] += amount
            else:
                aging["over_90"] += amount
        return {"aging": {key: float(value) for key, value in aging.items()}, "total_outstanding": float(sum(aging.values(), Decimal("0")))}

    def industry_report(self, tenant_id, industry):
        industry = str(industry or "").strip().lower()
        if industry == "trading":
            return self._trading_report(tenant_id)
        if industry == "restaurant":
            return self._restaurant_report(tenant_id)
        if industry == "manufacturing":
            return self._manufacturing_report(tenant_id)
        return {"error": {"code": "UNSUPPORTED_INDUSTRY", "message": f"Report for {industry} is not available"}}

    def _trading_report(self, tenant_id):
        return {
            "sales_orders": self._scalar("SELECT COUNT(*) FROM dbp_trading_sales_orders WHERE tenant_id=:t", {"t": tenant_id}),
            "purchase_orders": self._scalar("SELECT COUNT(*) FROM dbp_trading_purchase_orders WHERE tenant_id=:t", {"t": tenant_id}),
            "customers": self._scalar("SELECT COUNT(*) FROM dbp_commerce_customers WHERE tenant_id=:t", {"t": tenant_id}),
            "suppliers": self._scalar("SELECT COUNT(*) FROM dbp_commerce_suppliers WHERE tenant_id=:t", {"t": tenant_id}),
        }

    def _restaurant_report(self, tenant_id):
        return {
            "menu_items": self._scalar("SELECT COUNT(*) FROM dbp_restaurant_menu_items WHERE tenant_id=:t", {"t": tenant_id}),
            "orders_today": self._scalar("SELECT COUNT(*) FROM dbp_restaurant_orders WHERE tenant_id=:t AND DATE(created_at)=CURRENT_DATE", {"t": tenant_id}),
            "tables": self._scalar("SELECT COUNT(*) FROM dbp_restaurant_tables WHERE tenant_id=:t", {"t": tenant_id}),
        }

    def _manufacturing_report(self, tenant_id):
        return {
            "work_orders": self._scalar("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t", {"t": tenant_id}),
            "in_progress": self._scalar("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='in_progress'", {"t": tenant_id}),
            "completed": self._scalar("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='completed'", {"t": tenant_id}),
        }

    def export_report(self, tenant_id, report_type, format="json"):
        report_type = str(report_type or "").strip().lower()
        if report_type == "profit_and_loss":
            data = self.profit_and_loss(tenant_id)
        elif report_type == "balance_sheet":
            data = self.balance_sheet(tenant_id)
        elif report_type == "cash_flow":
            data = self.cash_flow(tenant_id)
        elif report_type == "sales":
            data = self.sales_report(tenant_id)
        elif report_type == "inventory":
            data = self.inventory_report(tenant_id)
        elif report_type == "customer_aging":
            data = self.customer_aging(tenant_id)
        else:
            return {"error": {"code": "UNKNOWN_REPORT_TYPE", "message": f"Unknown report type: {report_type}"}}
        return {"report_type": report_type, "format": format, "generated_at": datetime.utcnow().isoformat() + "Z", "data": data}
