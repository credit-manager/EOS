"""
EOS Advanced Analytics Engine — P65
Executive Dashboard + KPIs + Period Comparisons + Drill-Down.

Provides:
- Revenue, Expenses, Profit analytics
- Sales & Purchase trends
- Cash flow analysis
- Project cost tracking
- Inventory analytics
- Employee performance
- Customer/Supplier analytics
- KPIs with period-over-period comparison
- Role-based dashboard data
- Business alerts (anomalies, thresholds)
"""

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal

logger = logging.getLogger("eos.analytics")

# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _period_range(period: str, reference_date: date | None = None) -> tuple[date, date]:
    """Return (start, end) dates for a named period."""
    ref = reference_date or date.today()
    if period == "today":
        return ref, ref
    elif period == "yesterday":
        return ref - timedelta(days=1), ref - timedelta(days=1)
    elif period == "this_week":
        start = ref - timedelta(days=ref.weekday())
        return start, ref
    elif period == "last_week":
        end = ref - timedelta(days=ref.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    elif period == "this_month":
        return ref.replace(day=1), ref
    elif period == "last_month":
        first_this = ref.replace(day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(day=1)
        return start, end
    elif period == "this_quarter":
        q = (ref.month - 1) // 3
        start = ref.replace(month=q * 3 + 1, day=1)
        return start, ref
    elif period == "last_quarter":
        q = (ref.month - 1) // 3
        first_this = ref.replace(month=q * 3 + 1, day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(month=((q - 1) * 3 + 1) if q > 0 else 10, day=1)
        return start, end
    elif period == "this_year":
        return ref.replace(month=1, day=1), ref
    elif period == "last_year":
        end = ref.replace(month=1, day=1) - timedelta(days=1)
        start = end.replace(month=1, day=1)
        return start, end
    return ref, ref


def _execute_query(sql: str, params: dict | None = None, tenant_id: str | None = None) -> list[dict]:
    """Execute SQL and return list of dicts."""
    db = SessionLocal()
    try:
        if tenant_id:
            sql = sql.replace("WHERE 1=1", "WHERE tenant_id = :_tid")
            if params is None:
                params = {}
            params["_tid"] = tenant_id
        result = db.execute(text(sql), params or {})
        rows = [dict(row._mapping) for row in result]
        return rows
    except Exception as e:
        logger.error(f"Query error: {e}")
        return []
    finally:
        db.close()


def _execute_scalar(sql: str, params: dict | None = None, tenant_id: str | None = None) -> float:
    """Execute SQL and return single scalar value."""
    rows = _execute_query(sql, params, tenant_id)
    if rows:
        val = next(iter(rows[0].values()))
        return _safe_float(val)
    return 0.0


# ═══════════════════════════════════════════════
# Executive Dashboard
# ═══════════════════════════════════════════════

def get_executive_summary(tenant_id: str, period: str = "this_month") -> dict[str, Any]:
    """Get executive summary for the given period."""
    start, end = _period_range(period)

    # Revenue (from sales invoices)
    revenue = _execute_scalar(f"""
        SELECT COALESCE(SUM(total_amount), 0) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}' AND status IN ('paid','approved')
        AND invoice_date BETWEEN '{start}' AND '{end}'
    """)

    # Expenses (from purchase orders + payments)
    expenses = _execute_scalar(f"""
        SELECT COALESCE(SUM(total_amount), 0) FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}' AND status IN ('approved','received')
        AND order_date BETWEEN '{start}' AND '{end}'
    """)

    # Net profit
    profit = revenue - expenses
    profit_margin = (profit / revenue * 100) if revenue > 0 else 0

    # Outstanding receivables
    receivables = _execute_scalar(f"""
        SELECT COALESCE(SUM(amount_due), 0) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}' AND status IN ('unpaid','partial')
    """)

    # Outstanding payables
    payables = _execute_scalar(f"""
        SELECT COALESCE(SUM(total_amount), 0) FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}' AND status IN ('approved','pending')
    """)

    # Active customers
    customers = _execute_scalar(f"""
        SELECT COUNT(DISTINCT id) FROM dbp_customers WHERE tenant_id = '{tenant_id}'
    """)

    # Active projects
    projects = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}' AND status NOT IN ('completed','cancelled')
    """)

    return {
        "period": period,
        "start_date": str(start),
        "end_date": str(end),
        "revenue": revenue,
        "expenses": expenses,
        "profit": profit,
        "profit_margin": round(profit_margin, 1),
        "receivables": receivables,
        "payables": payables,
        "cash_position": revenue - expenses - receivables + payables,
        "active_customers": int(customers),
        "active_projects": int(projects),
    }


def get_revenue_trend(tenant_id: str, months: int = 12) -> list[dict[str, Any]]:
    """Get monthly revenue trend for the last N months."""
    rows = _execute_query(f"""
        SELECT
            DATE_TRUNC('month', invoice_date)::date AS month,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COUNT(*) AS invoice_count
        FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date >= CURRENT_DATE - INTERVAL '{months} months'
        AND status IN ('paid','approved')
        GROUP BY DATE_TRUNC('month', invoice_date)
        ORDER BY month
    """)
    return [{"month": str(r["month"]), "revenue": _safe_float(r["revenue"]),
             "invoice_count": int(r["invoice_count"])} for r in rows]


def get_expenses_trend(tenant_id: str, months: int = 12) -> list[dict[str, Any]]:
    """Get monthly expenses trend."""
    rows = _execute_query(f"""
        SELECT
            DATE_TRUNC('month', order_date)::date AS month,
            COALESCE(SUM(total_amount), 0) AS expenses,
            COUNT(*) AS order_count
        FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}'
        AND order_date >= CURRENT_DATE - INTERVAL '{months} months'
        AND status IN ('approved','received')
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month
    """)
    return [{"month": str(r["month"]), "expenses": _safe_float(r["expenses"]),
             "order_count": int(r["order_count"])} for r in rows]


def get_profit_trend(tenant_id: str, months: int = 12) -> list[dict[str, Any]]:
    """Get monthly profit trend (revenue - expenses)."""
    rev = {r["month"]: _safe_float(r["revenue"]) for r in get_revenue_trend(tenant_id, months)}
    exp = {r["month"]: _safe_float(r["expenses"]) for r in get_expenses_trend(tenant_id, months)}
    all_months = sorted(set(list(rev.keys()) + list(exp.keys())))
    return [{"month": m, "revenue": rev.get(m, 0), "expenses": exp.get(m, 0),
             "profit": rev.get(m, 0) - exp.get(m, 0)} for m in all_months]


def get_cash_flow(tenant_id: str, months: int = 6) -> list[dict[str, Any]]:
    """Get cash flow analysis."""
    rows = _execute_query(f"""
        SELECT
            DATE_TRUNC('month', payment_date)::date AS month,
            COALESCE(SUM(CASE WHEN payment_type = 'in' THEN amount ELSE 0 END), 0) AS inflow,
            COALESCE(SUM(CASE WHEN payment_type = 'out' THEN amount ELSE 0 END), 0) AS outflow
        FROM dbp_payments
        WHERE tenant_id = '{tenant_id}'
        AND payment_date >= CURRENT_DATE - INTERVAL '{months} months'
        GROUP BY DATE_TRUNC('month', payment_date)
        ORDER BY month
    """)
    result = []
    cumulative = 0
    for r in rows:
        inflow = _safe_float(r["inflow"])
        outflow = _safe_float(r["outflow"])
        net = inflow - outflow
        cumulative += net
        result.append({
            "month": str(r["month"]),
            "inflow": inflow,
            "outflow": outflow,
            "net": net,
            "cumulative": cumulative,
        })
    return result


# ═══════════════════════════════════════════════
# Sales Analytics
# ═══════════════════════════════════════════════

def get_sales_summary(tenant_id: str, period: str = "this_month") -> dict[str, Any]:
    """Get sales summary for period."""
    start, end = _period_range(period)

    total_invoices = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date BETWEEN '{start}' AND '{end}'
    """)

    total_revenue = _execute_scalar(f"""
        SELECT COALESCE(SUM(total_amount), 0) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date BETWEEN '{start}' AND '{end}'
        AND status IN ('paid','approved')
    """)

    avg_invoice = _execute_scalar(f"""
        SELECT COALESCE(AVG(total_amount), 0) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date BETWEEN '{start}' AND '{end}'
    """)

    paid_count = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date BETWEEN '{start}' AND '{end}'
        AND status = 'paid'
    """)

    unpaid_count = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_sales_invoices
        WHERE tenant_id = '{tenant_id}'
        AND invoice_date BETWEEN '{start}' AND '{end}'
        AND status IN ('unpaid','partial')
    """)

    return {
        "period": period,
        "total_invoices": int(total_invoices),
        "total_revenue": total_revenue,
        "average_invoice": round(avg_invoice, 2),
        "paid_count": int(paid_count),
        "unpaid_count": int(unpaid_count),
        "collection_rate": round((paid_count / total_invoices * 100) if total_invoices > 0 else 0, 1),
    }


def get_top_customers(tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get top customers by revenue."""
    rows = _execute_query(f"""
        SELECT
            c.id,
            c.name,
            COALESCE(SUM(si.total_amount), 0) AS total_revenue,
            COUNT(si.id) AS invoice_count
        FROM dbp_customers c
        LEFT JOIN dbp_sales_invoices si ON si.customer_id = c.id
            AND si.tenant_id = c.tenant_id AND si.status IN ('paid','approved')
        WHERE c.tenant_id = '{tenant_id}'
        GROUP BY c.id, c.name
        ORDER BY total_revenue DESC
        LIMIT {limit}
    """)
    return [{"customer_id": r["id"], "name": r["name"],
             "revenue": _safe_float(r["total_revenue"]),
             "invoices": int(r["invoice_count"])} for r in rows]


def get_sales_by_period(tenant_id: str) -> dict[str, Any]:
    """Get sales comparison across periods."""
    this_month = get_sales_summary(tenant_id, "this_month")
    last_month = get_sales_summary(tenant_id, "last_month")
    this_year = get_sales_summary(tenant_id, "this_year")

    def _change(curr, prev):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round((curr - prev) / prev * 100, 1)

    return {
        "this_month": this_month,
        "last_month": last_month,
        "this_year": this_year,
        "changes": {
            "revenue_change": _change(this_month["total_revenue"], last_month["total_revenue"]),
            "invoice_change": _change(this_month["total_invoices"], last_month["total_invoices"]),
        }
    }


# ═══════════════════════════════════════════════
# Purchase Analytics
# ═══════════════════════════════════════════════

def get_purchase_summary(tenant_id: str, period: str = "this_month") -> dict[str, Any]:
    """Get purchase summary for period."""
    start, end = _period_range(period)

    total_orders = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}'
        AND order_date BETWEEN '{start}' AND '{end}'
    """)

    total_amount = _execute_scalar(f"""
        SELECT COALESCE(SUM(total_amount), 0) FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}'
        AND order_date BETWEEN '{start}' AND '{end}'
        AND status IN ('approved','received')
    """)

    pending = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_purchase_orders
        WHERE tenant_id = '{tenant_id}'
        AND order_date BETWEEN '{start}' AND '{end}'
        AND status = 'pending'
    """)

    return {
        "period": period,
        "total_orders": int(total_orders),
        "total_amount": total_amount,
        "pending_orders": int(pending),
        "approval_rate": round(((total_orders - pending) / total_orders * 100) if total_orders > 0 else 0, 1),
    }


def get_top_suppliers(tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get top suppliers by purchase amount."""
    rows = _execute_query(f"""
        SELECT
            s.id,
            s.name,
            COALESCE(SUM(po.total_amount), 0) AS total_purchases,
            COUNT(po.id) AS order_count
        FROM dbp_suppliers s
        LEFT JOIN dbp_purchase_orders po ON po.supplier_id = s.id
            AND po.tenant_id = s.tenant_id AND po.status IN ('approved','received')
        WHERE s.tenant_id = '{tenant_id}'
        GROUP BY s.id, s.name
        ORDER BY total_purchases DESC
        LIMIT {limit}
    """)
    return [{"supplier_id": r["id"], "name": r["name"],
             "purchases": _safe_float(r["total_purchases"]),
             "orders": int(r["order_count"])} for r in rows]


# ═══════════════════════════════════════════════
# Inventory Analytics
# ═══════════════════════════════════════════════

def get_inventory_summary(tenant_id: str) -> dict[str, Any]:
    """Get inventory summary."""
    total_items = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_items WHERE tenant_id = '{tenant_id}'
    """)

    total_stock_value = _execute_scalar(f"""
        SELECT COALESCE(SUM(s.quantity * s.unit_cost), 0)
        FROM dbp_stock s WHERE s.tenant_id = '{tenant_id}'
    """)

    low_stock = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_stock s
        WHERE s.tenant_id = '{tenant_id}'
        AND s.quantity <= COALESCE(s.reorder_level, 0)
        AND s.reorder_level > 0
    """)

    warehouses = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_warehouses WHERE tenant_id = '{tenant_id}'
    """)

    return {
        "total_items": int(total_items),
        "total_stock_value": total_stock_value,
        "low_stock_items": int(low_stock),
        "warehouses": int(warehouses),
    }


def get_stock_movements(tenant_id: str, days: int = 30) -> list[dict[str, Any]]:
    """Get stock movements trend."""
    rows = _execute_query(f"""
        SELECT
            DATE_TRUNC('day', movement_date)::date AS day,
            SUM(CASE WHEN movement_type = 'in' THEN quantity ELSE 0 END) AS stock_in,
            SUM(CASE WHEN movement_type = 'out' THEN quantity ELSE 0 END) AS stock_out
        FROM dbp_stock_movements
        WHERE tenant_id = '{tenant_id}'
        AND movement_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY DATE_TRUNC('day', movement_date)
        ORDER BY day
    """)
    return [{"date": str(r["day"]), "in": _safe_float(r["stock_in"]),
             "out": _safe_float(r["stock_out"])} for r in rows]


# ═══════════════════════════════════════════════
# Project Analytics
# ═══════════════════════════════════════════════

def get_project_summary(tenant_id: str) -> dict[str, Any]:
    """Get project portfolio summary."""
    total = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_projects WHERE tenant_id = '{tenant_id}'
    """)

    active = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}' AND status NOT IN ('completed','cancelled')
    """)

    completed = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}' AND status = 'completed'
    """)

    total_budget = _execute_scalar(f"""
        SELECT COALESCE(SUM(budget), 0) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}'
    """)

    total_spent = _execute_scalar(f"""
        SELECT COALESCE(SUM(actual_cost), 0) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}'
    """)

    overdue = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_projects
        WHERE tenant_id = '{tenant_id}'
        AND end_date < CURRENT_DATE
        AND status NOT IN ('completed','cancelled')
    """)

    return {
        "total_projects": int(total),
        "active": int(active),
        "completed": int(completed),
        "overdue": int(overdue),
        "total_budget": total_budget,
        "total_spent": total_spent,
        "budget_utilization": round((total_spent / total_budget * 100) if total_budget > 0 else 0, 1),
    }


def get_project_cost_breakdown(tenant_id: str) -> list[dict[str, Any]]:
    """Get cost breakdown per project."""
    rows = _execute_query(f"""
        SELECT
            p.id,
            p.name,
            COALESCE(p.budget, 0) AS budget,
            COALESCE(p.actual_cost, 0) AS actual_cost,
            COALESCE(SUM(pte.hours * pte.rate), 0) AS labor_cost,
            p.status
        FROM dbp_projects p
        LEFT JOIN dbp_project_time_entries pte ON pte.project_id = p.id AND pte.tenant_id = p.tenant_id
        WHERE p.tenant_id = '{tenant_id}'
        GROUP BY p.id, p.name, p.budget, p.actual_cost, p.status
        ORDER BY actual_cost DESC
        LIMIT 20
    """)
    return [{"project_id": r["id"], "name": r["name"],
             "budget": _safe_float(r["budget"]),
             "actual_cost": _safe_float(r["actual_cost"]),
             "labor_cost": _safe_float(r["labor_cost"]),
             "variance": _safe_float(r["budget"]) - _safe_float(r["actual_cost"]),
             "status": r["status"]} for r in rows]


# ═══════════════════════════════════════════════
# HR Analytics
# ═══════════════════════════════════════════════

def get_hr_summary(tenant_id: str) -> dict[str, Any]:
    """Get HR summary."""
    total_employees = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_employees WHERE tenant_id = '{tenant_id}' AND status = 'active'
    """)

    departments = _execute_scalar(f"""
        SELECT COUNT(DISTINCT department) FROM dbp_employees
        WHERE tenant_id = '{tenant_id}' AND status = 'active'
    """)

    total_payroll = _execute_scalar(f"""
        SELECT COALESCE(SUM(net_amount), 0) FROM dbp_payroll_runs
        WHERE tenant_id = '{tenant_id}' AND status = 'paid'
    """)

    pending_leave = _execute_scalar(f"""
        SELECT COUNT(*) FROM dbp_leave_requests
        WHERE tenant_id = '{tenant_id}' AND status = 'pending'
    """)

    return {
        "total_employees": int(total_employees),
        "departments": int(departments),
        "total_payroll": total_payroll,
        "pending_leave_requests": int(pending_leave),
    }


# ═══════════════════════════════════════════════
# KPI Engine
# ═══════════════════════════════════════════════

def get_kpis(tenant_id: str, period: str = "this_month") -> list[dict[str, Any]]:
    """Get all KPIs with period-over-period comparison."""
    exec_summary = get_executive_summary(tenant_id, period)
    prev_period = "last_month" if period == "this_month" else "last_year"
    prev_summary = get_executive_summary(tenant_id, prev_period)

    def _kpi(name: str, current: float, previous: float, format_type: str = "number",
             higher_is_better: bool = True) -> dict[str, Any]:
        change = ((current - previous) / previous * 100) if previous != 0 else (100.0 if current > 0 else 0.0)
        trend = "up" if change > 0 else ("down" if change < 0 else "flat")
        if not higher_is_better:
            trend = "down" if change > 0 else ("up" if change < 0 else "flat")
        return {
            "name": name,
            "current": round(current, 2),
            "previous": round(previous, 2),
            "change": round(change, 1),
            "trend": trend,
            "format": format_type,
        }

    return [
        _kpi("revenue", exec_summary["revenue"], prev_summary["revenue"], "currency", True),
        _kpi("expenses", exec_summary["expenses"], prev_summary["expenses"], "currency", False),
        _kpi("profit", exec_summary["profit"], prev_summary["profit"], "currency", True),
        _kpi("profit_margin", exec_summary["profit_margin"], prev_summary["profit_margin"], "percent", True),
        _kpi("receivables", exec_summary["receivables"], prev_summary["receivables"], "currency", False),
        _kpi("payables", exec_summary["payables"], prev_summary["payables"], "currency", False),
        _kpi("active_customers", exec_summary["active_customers"], prev_summary["active_customers"], "number", True),
        _kpi("active_projects", exec_summary["active_projects"], prev_summary["active_projects"], "number", True),
    ]


# ═══════════════════════════════════════════════
# Role-Based Dashboards
# ═══════════════════════════════════════════════

def get_dashboard_for_role(tenant_id: str, role: str, period: str = "this_month") -> dict[str, Any]:
    """Get dashboard data tailored to a specific role."""
    base = {
        "role": role,
        "period": period,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    if role in ("owner", "ceo", "admin"):
        base["summary"] = get_executive_summary(tenant_id, period)
        base["kpis"] = get_kpis(tenant_id, period)
        base["revenue_trend"] = get_revenue_trend(tenant_id, 12)
        base["profit_trend"] = get_profit_trend(tenant_id, 12)
        base["top_customers"] = get_top_customers(tenant_id, 5)
        base["top_suppliers"] = get_top_suppliers(tenant_id, 5)
        base["project_summary"] = get_project_summary(tenant_id)
        base["hr_summary"] = get_hr_summary(tenant_id)

    elif role == "finance":
        base["summary"] = get_executive_summary(tenant_id, period)
        base["kpis"] = get_kpis(tenant_id, period)
        base["revenue_trend"] = get_revenue_trend(tenant_id, months=12)
        base["expenses_trend"] = get_expenses_trend(tenant_id, 12)
        base["cash_flow"] = get_cash_flow(tenant_id, 6)
        base["sales_by_period"] = get_sales_by_period(tenant_id)
        base["receivables"] = get_top_customers(tenant_id, 10)
        base["payables"] = get_top_suppliers(tenant_id, 10)

    elif role == "project_manager":
        base["project_summary"] = get_project_summary(tenant_id)
        base["project_costs"] = get_project_cost_breakdown(tenant_id)
        base["hr_summary"] = get_hr_summary(tenant_id)

    elif role == "procurement":
        base["purchase_summary"] = get_purchase_summary(tenant_id, period)
        base["top_suppliers"] = get_top_suppliers(tenant_id, 10)
        base["inventory"] = get_inventory_summary(tenant_id)

    elif role == "warehouse":
        base["inventory"] = get_inventory_summary(tenant_id)
        base["stock_movements"] = get_stock_movements(tenant_id, 30)

    else:
        base["summary"] = get_executive_summary(tenant_id, period)
        base["kpis"] = get_kpis(tenant_id, period)

    return base


# ═══════════════════════════════════════════════
# Business Alerts Engine
# ═══════════════════════════════════════════════

def get_business_alerts(tenant_id: str) -> list[dict[str, Any]]:
    """Generate business alerts based on thresholds and anomalies."""
    alerts = []
    summary = get_executive_summary(tenant_id, "this_month")

    # Revenue dropped
    prev = get_executive_summary(tenant_id, "last_month")
    if prev["revenue"] > 0 and summary["revenue"] < prev["revenue"] * 0.8:
        alerts.append({
            "type": "warning",
            "category": "revenue",
            "title": "Revenue Decline",
            "message": f"Revenue dropped {round((1 - summary['revenue']/prev['revenue'])*100)}% from last month",
            "action": "Review sales pipeline and customer retention",
        })

    # High receivables
    if summary["receivables"] > summary["revenue"] * 0.5:
        alerts.append({
            "type": "warning",
            "category": "receivables",
            "title": "High Outstanding Receivables",
            "message": f"Receivables ({summary['receivables']:.0f}) exceed 50% of monthly revenue",
            "action": "Follow up on overdue invoices",
        })

    # Low stock
    inv = get_inventory_summary(tenant_id)
    if inv["low_stock_items"] > 0:
        alerts.append({
            "type": "warning",
            "category": "inventory",
            "title": "Low Stock Items",
            "message": f"{inv['low_stock_items']} item(s) are at or below reorder level",
            "action": "Review and place purchase orders",
        })

    # Overdue projects
    proj = get_project_summary(tenant_id)
    if proj["overdue"] > 0:
        alerts.append({
            "type": "danger",
            "category": "projects",
            "title": "Overdue Projects",
            "message": f"{proj['overdue']} project(s) are past their deadline",
            "action": "Review project timelines and resource allocation",
        })

    # Budget overrun
    if proj["budget_utilization"] > 100:
        alerts.append({
            "type": "danger",
            "category": "budget",
            "title": "Budget Overrun",
            "message": f"Project spending ({proj['budget_utilization']}%) exceeds budget",
            "action": "Review and control project costs",
        })

    # Negative profit
    if summary["profit"] < 0:
        alerts.append({
            "type": "danger",
            "category": "profit",
            "title": "Negative Profit",
            "message": f"Operating at a loss: {summary['profit']:.0f}",
            "action": "Review expenses and pricing strategy",
        })

    return alerts


# ═══════════════════════════════════════════════
# Drill-Down
# ═══════════════════════════════════════════════

def drill_down(tenant_id: str, entity_type: str, entity_id: str) -> dict[str, Any]:
    """Drill-down from KPI to source documents."""
    db = SessionLocal()
    try:
        if entity_type == "invoice":
            row = db.execute(text(f"""
                SELECT * FROM dbp_sales_invoices
                WHERE id = '{entity_id}' AND tenant_id = '{tenant_id}'
            """)).mappings().first()
            return dict(row) if row else {}

        elif entity_type == "purchase_order":
            row = db.execute(text(f"""
                SELECT * FROM dbp_purchase_orders
                WHERE id = '{entity_id}' AND tenant_id = '{tenant_id}'
            """)).mappings().first()
            return dict(row) if row else {}

        elif entity_type == "project":
            row = db.execute(text(f"""
                SELECT * FROM dbp_projects
                WHERE id = '{entity_id}' AND tenant_id = '{tenant_id}'
            """)).mappings().first()
            return dict(row) if row else {}

        elif entity_type == "payment":
            row = db.execute(text(f"""
                SELECT * FROM dbp_payments
                WHERE id = '{entity_id}' AND tenant_id = '{tenant_id}'
            """)).mappings().first()
            return dict(row) if row else {}

        return {}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# AnalyticsEngine — CRUD class for dashboards, widgets, pipelines,
# pipeline runs, and alerts. Used by routers/analytics.py and
# routers/dashboards.py. Not related to the P65 executive functions above.
# ═══════════════════════════════════════════════════════════════


class AnalyticsEngine:
    """CRUD engine for dashboard/widget/pipeline/alert management."""

    def __init__(self, db: Session):
        self.db = db

    # ── Dashboards ──────────────────────────────────────────

    def list_dashboards(self, tenant_id: str, dashboard_type: str | None = None):
        sql = "SELECT id, dashboard_name, dashboard_type, layout_config, is_shared, owner_id, created_at FROM dbp_dashboards WHERE tenant_id = :tid"
        params: dict = {"tid": tenant_id}
        if dashboard_type:
            sql += " AND dashboard_type = :dt"
            params["dt"] = dashboard_type
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_dashboard(self, tenant_id: str, name: str, dtype: str,
                         layout_config=None, is_shared=False, owner_id=None):
        did = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_dashboards (id, tenant_id, dashboard_name, dashboard_type, "
            "layout_config, is_shared, owner_id) VALUES (:id, :tid, :name, :dt, :lc, :sh, :oid)"
        ), {"id": did, "tid": tenant_id, "name": name, "dt": dtype,
            "lc": json.dumps(layout_config) if layout_config else None,
            "sh": is_shared, "oid": owner_id})
        return did

    def get_dashboard(self, tenant_id: str, dashboard_id: str):
        row = self.db.execute(text(
            "SELECT id, dashboard_name, dashboard_type, layout_config, is_shared, owner_id, created_at "
            "FROM dbp_dashboards WHERE id = :id AND tenant_id = :tid"
        ), {"id": dashboard_id, "tid": tenant_id}).mappings().first()
        return dict(row) if row else None

    def delete_dashboard(self, tenant_id: str, dashboard_id: str):
        result = self.db.execute(text(
            "DELETE FROM dbp_dashboards WHERE id = :id AND tenant_id = :tid"
        ), {"id": dashboard_id, "tid": tenant_id})
        return result.rowcount > 0

    # ── Widgets ─────────────────────────────────────────────

    def list_widgets(self, dashboard_id: str):
        rows = self.db.execute(text(
            "SELECT id, widget_type, title, config, position_x, position_y, width, height "
            "FROM dbp_dashboard_widgets WHERE dashboard_id = :did ORDER BY position_y, position_x"
        ), {"did": dashboard_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_widget(self, dashboard_id: str, widget_type: str,
                      title=None, config=None, position_x=0, position_y=0, width=6, height=4):
        wid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_dashboard_widgets (id, dashboard_id, widget_type, title, config, "
            "position_x, position_y, width, height) VALUES (:id, :did, :wt, :t, :cfg, :px, :py, :w, :h)"
        ), {"id": wid, "did": dashboard_id, "wt": widget_type, "t": title,
            "cfg": json.dumps(config) if config else None,
            "px": position_x, "py": position_y, "w": width, "h": height})
        return wid

    def delete_widget(self, widget_id: str):
        result = self.db.execute(text(
            "DELETE FROM dbp_dashboard_widgets WHERE id = :id"
        ), {"id": widget_id})
        return result.rowcount > 0

    # ── Pipelines ───────────────────────────────────────────

    def list_pipelines(self, tenant_id: str, status: str | None = None):
        sql = "SELECT id, pipeline_name, source_type, target_type, config, schedule, status, created_at FROM dbp_pipelines WHERE tenant_id = :tid"
        params: dict = {"tid": tenant_id}
        if status:
            sql += " AND status = :st"
            params["st"] = status
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_pipeline(self, tenant_id: str, name: str, source_type: str,
                        target_type: str, config=None, schedule=None):
        pid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_pipelines (id, tenant_id, pipeline_name, source_type, "
            "target_type, config, schedule, status) VALUES (:id, :tid, :name, :st, :tt, :cfg, :sch, 'draft')"
        ), {"id": pid, "tid": tenant_id, "name": name, "st": source_type,
            "tt": target_type, "cfg": json.dumps(config) if config else None, "sch": schedule})
        return pid

    def get_pipeline(self, tenant_id: str, pipeline_id: str):
        row = self.db.execute(text(
            "SELECT id, pipeline_name, source_type, target_type, config, schedule, status, created_at "
            "FROM dbp_pipelines WHERE id = :id AND tenant_id = :tid"
        ), {"id": pipeline_id, "tid": tenant_id}).mappings().first()
        return dict(row) if row else None

    def update_pipeline(self, tenant_id: str, pipeline_id: str, **kwargs):
        allowed = {"pipeline_name", "source_type", "target_type", "config", "schedule", "status"}
        sets, params = [], {"id": pipeline_id, "tid": tenant_id}
        for k, v in kwargs.items():
            if k in allowed:
                val = json.dumps(v) if k == "config" else v
                sets.append(f"{k} = :{k}")
                params[k] = val
        if sets:
            self.db.execute(text(
                f"UPDATE dbp_pipelines SET {', '.join(sets)} WHERE id = :id AND tenant_id = :tid"
            ), params)
        return self.get_pipeline(tenant_id, pipeline_id)

    # ── Pipeline Runs ───────────────────────────────────────

    def list_pipeline_runs(self, tenant_id: str, pipeline_id: str | None = None,
                           status: str | None = None, limit: int = 20):
        sql = "SELECT id, pipeline_id, status, started_at, completed_at, records_processed, records_failed FROM dbp_pipeline_runs WHERE tenant_id = :tid"
        params: dict = {"tid": tenant_id}
        if pipeline_id:
            sql += " AND pipeline_id = :pid"
            params["pid"] = pipeline_id
        if status:
            sql += " AND status = :st"
            params["st"] = status
        sql += " ORDER BY started_at DESC LIMIT :lim"
        params["lim"] = limit
        rows = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_pipeline_run(self, pipeline_id: str, tenant_id: str):
        rid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_pipeline_runs (id, pipeline_id, tenant_id, status, started_at) "
            "VALUES (:id, :pid, :tid, 'running', NOW())"
        ), {"id": rid, "pid": pipeline_id, "tid": tenant_id})
        return rid

    def complete_pipeline_run(self, run_id: str, records_processed: int = 0,
                              records_failed: int = 0, error_message: str | None = None):
        self.db.execute(text(
            "UPDATE dbp_pipeline_runs SET status = 'completed', completed_at = NOW(), "
            "records_processed = :rp, records_failed = :rf, error_message = :em WHERE id = :id"
        ), {"id": run_id, "rp": records_processed, "rf": records_failed, "em": error_message})
        return {"id": run_id, "status": "completed"}

    # ── Alerts ──────────────────────────────────────────────

    def list_alerts(self, tenant_id: str, is_active: bool | None = None):
        sql = "SELECT id, alert_name, metric_name, condition, threshold_value, is_active, created_at FROM dbp_alerts WHERE tenant_id = :tid"
        params: dict = {"tid": tenant_id}
        if is_active is not None:
            sql += " AND is_active = :act"
            params["act"] = is_active
        sql += " ORDER BY created_at DESC"
        rows = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def create_alert(self, tenant_id: str, alert_name: str, metric_name: str,
                     condition: str, threshold_value: float, notification_channels=None):
        aid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_alerts (id, tenant_id, alert_name, metric_name, condition, "
            "threshold_value, notification_channels, is_active) VALUES (:id, :tid, :an, :mn, :cond, :tv, :nc, true)"
        ), {"id": aid, "tid": tenant_id, "an": alert_name, "mn": metric_name,
            "cond": condition, "tv": threshold_value,
            "nc": json.dumps(notification_channels) if notification_channels else None})
        return aid

    def trigger_alert(self, tenant_id: str, alert_id: str):
        row = self.db.execute(text(
            "SELECT id, alert_name FROM dbp_alerts WHERE id = :id AND tenant_id = :tid"
        ), {"id": alert_id, "tid": tenant_id}).mappings().first()
        if not row:
            return None
        return {"id": str(row["id"]), "alert_name": row["alert_name"], "triggered": True}

    def delete_alert(self, tenant_id: str, alert_id: str):
        result = self.db.execute(text(
            "DELETE FROM dbp_alerts WHERE id = :id AND tenant_id = :tid"
        ), {"id": alert_id, "tid": tenant_id})
        return result.rowcount > 0

    # ── Dashboard execution (for dashboards.py) ─────────────

    def execute_dashboard(self, dashboard_id: str):
        dash = self.db.execute(text(
            "SELECT id, dashboard_name, dashboard_type FROM dbp_dashboards WHERE id = :id"
        ), {"id": dashboard_id}).mappings().first()
        if not dash:
            return {"error": "Dashboard not found"}
        widgets = self.db.execute(text(
            "SELECT id, widget_type, title, entity_code, position_x, position_y, width, height, query_config "
            "FROM dbp_dashboard_widgets WHERE dashboard_id = :did AND is_active = true"
        ), {"did": dashboard_id}).fetchall()
        return {
            "id": str(dash["id"]),
            "dashboard_name": dash["dashboard_name"],
            "dashboard_type": dash["dashboard_type"],
            "widgets": [dict(w._mapping) for w in widgets],
        }

    def _validate_entity(self, entity_code: str) -> bool:
        row = self.db.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t AND table_schema = 'public'"
        ), {"t": f"dbp_{entity_code}s"}).fetchone()
        return row is not None

