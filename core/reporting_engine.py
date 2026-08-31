"""
EOS Advanced Reporting Engine
Financial, operational, and industry-specific reports
"""
import uuid
from datetime import datetime, timedelta
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

    def profit_and_loss(self, tenant_id, start_date=None, end_date=None):
        start = start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        revenue = self._scalar(
            "SELECT COALESCE(SUM(total),0) FROM dbp_trading_sales_orders "
            "WHERE tenant_id = :t AND status IN ('confirmed','completed','paid','invoiced') "
            "AND created_at::date BETWEEN :s AND :e",
            {"t": tenant_id, "s": start, "e": end})
        return {
            "period": {"start": start, "end": end},
            "revenue": float(revenue),
            "cost_of_goods": 0,
            "gross_profit": float(revenue),
            "gross_margin": 100 if revenue else 0
        }

    def balance_sheet(self, tenant_id):
        assets = self._scalar(
            "SELECT COALESCE(SUM(current_balance),0) FROM dbp_bank_accounts WHERE tenant_id = :t",
            {"t": tenant_id})
        inventory = self._scalar(
            "SELECT COALESCE(SUM(on_hand * unit_cost),0) FROM dbp_commerce_stock WHERE tenant_id = :t",
            {"t": tenant_id})
        receivables = self._scalar(
            "SELECT COALESCE(SUM(balance),0) FROM dbp_trading_sales_invoices "
            "WHERE tenant_id = :t AND status != 'paid'",
            {"t": tenant_id})
        payables = self._scalar(
            "SELECT COALESCE(SUM(balance),0) FROM dbp_trading_purchase_invoices "
            "WHERE tenant_id = :t AND status != 'paid'",
            {"t": tenant_id})
        return {
            "assets": {
                "cash": float(assets),
                "inventory": float(inventory),
                "accounts_receivable": float(receivables),
                "total": float(assets + inventory + receivables)
            },
            "liabilities": {
                "accounts_payable": float(payables),
                "total": float(payables)
            },
            "equity": {
                "total": float(assets + inventory + receivables - payables)
            }
        }

    def cash_flow(self, tenant_id, days=30):
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        inflows = self._scalar(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND transaction_type = 'payment' AND status = 'completed' "
            "AND created_at::date >= :s",
            {"t": tenant_id, "s": start})
        outflows = self._scalar(
            "SELECT COALESCE(SUM(amount),0) FROM dbp_payment_transactions "
            "WHERE tenant_id = :t AND transaction_type = 'refund' AND status = 'completed' "
            "AND created_at::date >= :s",
            {"t": tenant_id, "s": start})
        return {
            "period_days": days,
            "inflows": float(inflows),
            "outflows": float(outflows),
            "net_cash_flow": float(inflows - outflows)
        }

    def sales_report(self, tenant_id, start_date=None, end_date=None):
        start = start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        orders = self._query(
            "SELECT DATE(created_at) as date, COUNT(*) as count, COALESCE(SUM(total),0) as amount "
            "FROM dbp_trading_sales_orders WHERE tenant_id = :t "
            "AND created_at::date BETWEEN :s AND :e GROUP BY DATE(created_at) ORDER BY date",
            {"t": tenant_id, "s": start, "e": end})
        top_customers = self._query(
            "SELECT customer_id, COUNT(*) as order_count, COALESCE(SUM(total),0) as total_amount "
            "FROM dbp_trading_sales_orders WHERE tenant_id = :t "
            "AND created_at::date BETWEEN :s AND :e "
            "GROUP BY customer_id ORDER BY total_amount DESC LIMIT 10",
            {"t": tenant_id, "s": start, "e": end})
        return {"period": {"start": start, "end": end}, "daily": orders, "top_customers": top_customers}

    def inventory_report(self, tenant_id):
        items = self._query(
            "SELECT ci.id, ci.name, cs.on_hand as qty_on_hand, cs.unit_cost, "
            "cs.on_hand * cs.unit_cost as stock_value, cs.warehouse_id "
            "FROM dbp_commerce_items ci "
            "JOIN dbp_commerce_stock cs ON ci.id = cs.item_id AND ci.tenant_id = cs.tenant_id "
            "WHERE ci.tenant_id = :t ORDER BY stock_value DESC",
            {"t": tenant_id})
        total_value = sum(i.get("stock_value", 0) for i in items)
        low_stock = [i for i in items if i.get("qty_on_hand", 0) <= 10]
        return {
            "total_items": len(items),
            "total_stock_value": float(total_value),
            "low_stock_items": len(low_stock),
            "items": items[:50]
        }

    def customer_aging(self, tenant_id):
        aging = {"current": 0, "30_days": 0, "60_days": 0, "90_days": 0, "over_90": 0}
        rows = self._query(
            "SELECT balance as total_amount, due_date, CURRENT_DATE - due_date::date as days_overdue "
            "FROM dbp_trading_sales_invoices WHERE tenant_id = :t AND status != 'paid'",
            {"t": tenant_id})
        for r in rows:
            days = r.get("days_overdue", 0) or 0
            amt = float(r.get("total_amount", 0))
            if days <= 0: aging["current"] += amt
            elif days <= 30: aging["30_days"] += amt
            elif days <= 60: aging["60_days"] += amt
            elif days <= 90: aging["90_days"] += amt
            else: aging["over_90"] += amt
        return {"aging": aging, "total_outstanding": sum(aging.values())}

    def industry_report(self, tenant_id, industry):
        if industry == "trading":
            return self._trading_report(tenant_id)
        elif industry == "restaurant":
            return self._restaurant_report(tenant_id)
        elif industry == "manufacturing":
            return self._manufacturing_report(tenant_id)
        return {"error": f"Report for {industry} not implemented"}

    def _trading_report(self, tenant_id):
        return {
            "sales_orders": self._scalar("SELECT COUNT(*) FROM dbp_trading_sales_orders WHERE tenant_id = :t", {"t": tenant_id}),
            "purchase_orders": self._scalar("SELECT COUNT(*) FROM dbp_trading_purchase_orders WHERE tenant_id = :t", {"t": tenant_id}),
            "customers": self._scalar("SELECT COUNT(*) FROM dbp_commerce_customers WHERE tenant_id = :t", {"t": tenant_id}),
            "suppliers": self._scalar("SELECT COUNT(*) FROM dbp_commerce_suppliers WHERE tenant_id = :t", {"t": tenant_id}),
        }

    def _restaurant_report(self, tenant_id):
        return {
            "menu_items": self._scalar("SELECT COUNT(*) FROM dbp_restaurant_menu_items WHERE tenant_id = :t", {"t": tenant_id}),
            "orders_today": self._scalar(
                "SELECT COUNT(*) FROM dbp_restaurant_orders WHERE tenant_id = :t AND DATE(created_at) = CURRENT_DATE",
                {"t": tenant_id}),
            "tables": self._scalar("SELECT COUNT(*) FROM dbp_restaurant_tables WHERE tenant_id = :t", {"t": tenant_id}),
        }

    def _manufacturing_report(self, tenant_id):
        return {
            "work_orders": self._scalar("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id = :t", {"t": tenant_id}),
            "in_progress": self._scalar(
                "SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id = :t AND status = 'in_progress'", {"t": tenant_id}),
            "completed": self._scalar(
                "SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id = :t AND status = 'completed'", {"t": tenant_id}),
        }

    def export_report(self, tenant_id, report_type, format="json"):
        if report_type == "profit_and_loss": data = self.profit_and_loss(tenant_id)
        elif report_type == "balance_sheet": data = self.balance_sheet(tenant_id)
        elif report_type == "cash_flow": data = self.cash_flow(tenant_id)
        elif report_type == "sales": data = self.sales_report(tenant_id)
        elif report_type == "inventory": data = self.inventory_report(tenant_id)
        else: return {"error": f"Unknown report type: {report_type}"}
        return {"report_type": report_type, "generated_at": datetime.now().isoformat(), "data": data}
