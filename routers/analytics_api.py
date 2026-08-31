"""
P71.4 Cross-Industry Analytics — CEO Dashboard API
====================================================
Consolidated view across all 6 industries.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, Depends
from typing import Optional

from database import get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import success_response, list_response

router = APIRouter(prefix="/analytics", tags=["Cross-Industry Analytics"])


# ═══════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════

@router.get("/overview")
def get_overview(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]

    industries = {}

    # Trading
    try:
        trading_orders = db.execute(text("SELECT COUNT(*) FROM dbp_trading_sales_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        trading_revenue = db.execute(text("SELECT COALESCE(SUM(total),0) FROM dbp_trading_sales_orders WHERE tenant_id=:t AND status IN ('confirmed','completed','paid','invoiced')"), {"t": t}).fetchone()[0] or 0
        industries["trading"] = {"orders": trading_orders, "revenue": float(trading_revenue)}
    except Exception:
        db.rollback()
        industries["trading"] = {"orders": 0, "revenue": 0}

    # Retail
    try:
        retail_orders = db.execute(text("SELECT COUNT(*) FROM dbp_retail_pos_sales WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        retail_revenue = db.execute(text("SELECT COALESCE(SUM(total),0) FROM dbp_retail_pos_sales WHERE tenant_id=:t AND status IN ('completed','paid')"), {"t": t}).fetchone()[0] or 0
        industries["retail"] = {"orders": retail_orders, "revenue": float(retail_revenue)}
    except Exception:
        db.rollback()
        industries["retail"] = {"orders": 0, "revenue": 0}

    # Restaurant
    try:
        rest_orders = db.execute(text("SELECT COUNT(*) FROM dbp_restaurant_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        rest_revenue = db.execute(text("SELECT COALESCE(SUM(total),0) FROM dbp_restaurant_orders WHERE tenant_id=:t AND status IN ('completed','paid')"), {"t": t}).fetchone()[0] or 0
        industries["restaurant"] = {"orders": rest_orders, "revenue": float(rest_revenue)}
    except Exception:
        db.rollback()
        industries["restaurant"] = {"orders": 0, "revenue": 0}

    # Construction
    try:
        constr_projects = db.execute(text("SELECT COUNT(*) FROM dbp_projects WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        constr_value = db.execute(text("SELECT COALESCE(SUM(budget),0) FROM dbp_projects WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        industries["construction"] = {"projects": constr_projects, "contract_value": float(constr_value)}
    except Exception:
        db.rollback()
        industries["construction"] = {"projects": 0, "contract_value": 0}

    # Manufacturing
    try:
        mfg_orders = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        mfg_completed = db.execute(text("SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='completed'"), {"t": t}).fetchone()[0] or 0
        industries["manufacturing"] = {"total_orders": mfg_orders, "completed": mfg_completed}
    except Exception:
        db.rollback()
        industries["manufacturing"] = {"total_orders": 0, "completed": 0}

    # Services
    try:
        svc_contracts = db.execute(text("SELECT COUNT(*) FROM dbp_svc_contracts WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        svc_revenue = db.execute(text("SELECT COALESCE(SUM(value),0) FROM dbp_svc_contracts WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        svc_projects = db.execute(text("SELECT COUNT(*) FROM dbp_svc_projects WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        industries["services"] = {"contracts": svc_contracts, "revenue": float(svc_revenue), "projects": svc_projects}
    except Exception:
        db.rollback()
        industries["services"] = {"contracts": 0, "revenue": 0, "projects": 0}

    # Users
    try:
        users = db.execute(text("SELECT COUNT(*) FROM users WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
    except Exception:
        db.rollback()
        users = 0

    return success_response("Cross-industry overview", {
        "industries": industries,
        "total_users": users,
        "active_industries": len([k for k, v in industries.items() if any(vv > 0 for vv in v.values() if isinstance(vv, (int, float)))]),
    })


# ═══════════════════════════════════════════════════
# BY INDUSTRY
# ═══════════════════════════════════════════════════

@router.get("/by-industry")
def get_by_industry(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    data = []

    # Commerce Engine (Trading + Retail)
    try:
        trading = db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total),0) "
            "FROM dbp_trading_sales_orders WHERE tenant_id=:t"), {"t": t}).fetchone()
        if trading:
            data.append({"industry": "trading", "metric": "orders", "count": trading[0] or 0, "revenue": float(trading[1] or 0)})
        retail = db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total),0) "
            "FROM dbp_retail_pos_sales WHERE tenant_id=:t"), {"t": t}).fetchone()
        if retail:
            data.append({"industry": "retail", "metric": "orders", "count": retail[0] or 0, "revenue": float(retail[1] or 0)})
    except Exception:
        pass

    # Restaurant
    try:
        c = db.execute(text("SELECT COUNT(*), COALESCE(SUM(total),0) FROM dbp_restaurant_orders WHERE tenant_id=:t"), {"t": t}).fetchone()
        data.append({"industry": "restaurant", "metric": "orders", "count": c[0] or 0, "revenue": float(c[1] or 0)})
    except Exception:
        pass

    # Construction
    try:
        c = db.execute(text("SELECT COUNT(*), COALESCE(SUM(contract_value),0) FROM dbp_construction_projects WHERE tenant_id=:t"), {"t": t}).fetchone()
        data.append({"industry": "construction", "metric": "projects", "count": c[0] or 0, "revenue": float(c[1] or 0)})
    except Exception:
        pass

    # Manufacturing
    try:
        c = db.execute(text("SELECT COUNT(*), COALESCE(SUM(qty_completed),0) FROM dbp_mfg_orders WHERE tenant_id=:t"), {"t": t}).fetchone()
        data.append({"industry": "manufacturing", "metric": "production_orders", "count": c[0] or 0, "units_produced": int(c[1] or 0)})
    except Exception:
        pass

    # Services
    try:
        c = db.execute(text("SELECT COUNT(*), COALESCE(SUM(value),0) FROM dbp_svc_contracts WHERE tenant_id=:t"), {"t": t}).fetchone()
        data.append({"industry": "services", "metric": "contracts", "count": c[0] or 0, "revenue": float(c[1] or 0)})
    except Exception:
        pass

    return list_response(data, len(data))


# ═══════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════

@router.get("/alerts")
def get_alerts(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    alerts = []

    # Low stock alerts
    try:
        low = db.execute(text(
            "SELECT item_name, qty_on_hand, reorder_level "
            "FROM dbp_commerce_stock WHERE tenant_id=:t AND qty_on_hand <= reorder_level AND reorder_level > 0 "
            "LIMIT 10"), {"t": t}).fetchall()
        for r in low:
            alerts.append({"type": "warning", "category": "inventory", "message": f"Low stock: {r[0]} ({r[1]} / reorder: {r[2]})"})
    except Exception:
        pass

    # Pending approvals
    try:
        pending = db.execute(text(
            "SELECT COUNT(*) FROM dbp_approve_requests WHERE tenant_id=:t AND status='pending'"), {"t": t}).fetchone()[0] or 0
        if pending > 0:
            alerts.append({"type": "info", "category": "approvals", "message": f"{pending} pending approval(s)"})
    except Exception:
        pass

    # Overdue invoices (Services)
    try:
        overdue = db.execute(text(
            "SELECT COUNT(*) FROM dbp_svc_invoices WHERE tenant_id=:t AND status IN ('sent','overdue') AND due_date < CURRENT_DATE"), {"t": t}).fetchone()[0] or 0
        if overdue > 0:
            alerts.append({"type": "error", "category": "invoices", "message": f"{overdue} overdue invoice(s)"})
    except Exception:
        pass

    # Stuck manufacturing orders
    try:
        stuck = db.execute(text(
            "SELECT COUNT(*) FROM dbp_mfg_orders WHERE tenant_id=:t AND status='in_progress'"), {"t": t}).fetchone()[0] or 0
        if stuck > 0:
            alerts.append({"type": "info", "category": "manufacturing", "message": f"{stuck} production order(s) in progress"})
    except Exception:
        pass

    # Unread notifications
    try:
        unread = db.execute(text(
            "SELECT COUNT(*) FROM dbp_notify_inbox WHERE tenant_id=:t AND user_id=:u AND is_read=FALSE"),
            {"t": t, "u": user["id"]}).fetchone()[0] or 0
        if unread > 0:
            alerts.append({"type": "info", "category": "notifications", "message": f"{unread} unread notification(s)"})
    except Exception:
        pass

    return list_response(alerts, len(alerts))


# ═══════════════════════════════════════════════════
# INVENTORY SUMMARY
# ═══════════════════════════════════════════════════

@router.get("/inventory-summary")
def inventory_summary(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    try:
        items = db.execute(text(
            "SELECT COUNT(*) FROM dbp_commerce_items WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        total_stock = db.execute(text(
            "SELECT COALESCE(SUM(qty_on_hand),0) FROM dbp_commerce_stock WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        total_value = db.execute(text(
            "SELECT COALESCE(SUM(qty_on_hand * unit_cost),0) FROM dbp_commerce_stock WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        low_stock = db.execute(text(
            "SELECT COUNT(*) FROM dbp_commerce_stock WHERE tenant_id=:t AND qty_on_hand <= reorder_level AND reorder_level > 0"), {"t": t}).fetchone()[0] or 0
        warehouses = db.execute(text(
            "SELECT COUNT(*) FROM dbp_commerce_warehouses WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        return success_response("Inventory summary", {
            "items": items, "total_stock": int(total_stock),
            "total_value": float(total_value), "low_stock_items": low_stock,
            "warehouses": warehouses
        })
    except Exception:
        return success_response("Inventory summary", {
            "items": 0, "total_stock": 0, "total_value": 0, "low_stock_items": 0, "warehouses": 0
        })


# ═══════════════════════════════════════════════════
# HR SUMMARY
# ═══════════════════════════════════════════════════

@router.get("/hr-summary")
def hr_summary(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    try:
        employees = db.execute(text("SELECT COUNT(*) FROM employees WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        departments = db.execute(text("SELECT COUNT(DISTINCT department) FROM employees WHERE tenant_id=:t AND department IS NOT NULL"), {"t": t}).fetchone()[0] or 0
        return success_response("HR summary", {"employees": employees, "departments": departments})
    except Exception:
        return success_response("HR summary", {"employees": 0, "departments": 0})


# ═══════════════════════════════════════════════════
# ACCOUNTING SUMMARY
# ═══════════════════════════════════════════════════

@router.get("/accounting-summary")
def accounting_summary(user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = user["tenant_id"]
    try:
        journals = db.execute(text("SELECT COUNT(*) FROM journals WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        accounts = db.execute(text("SELECT COUNT(*) FROM chart_of_accounts WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        total_debit = db.execute(text("SELECT COALESCE(SUM(debit),0) FROM journals WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        total_credit = db.execute(text("SELECT COALESCE(SUM(credit),0) FROM journals WHERE tenant_id=:t"), {"t": t}).fetchone()[0] or 0
        return success_response("Accounting summary", {
            "journals": journals, "accounts": accounts,
            "total_debit": float(total_debit), "total_credit": float(total_credit),
            "balanced": abs(float(total_debit) - float(total_credit)) < 0.01
        })
    except Exception:
        return success_response("Accounting summary", {
            "journals": 0, "accounts": 0, "total_debit": 0, "total_credit": 0, "balanced": True
        })
