"""
EOS Analytics Router — P65
Advanced Analytics & Executive Dashboard API endpoints.

Endpoints:
    GET  /api/v1/analytics/executive        — Executive summary
    GET  /api/v1/analytics/kpis             — KPIs with comparison
    GET  /api/v1/analytics/revenue-trend    — Monthly revenue trend
    GET  /api/v1/analytics/expenses-trend   — Monthly expenses trend
    GET  /api/v1/analytics/profit-trend     — Profit trend
    GET  /api/v1/analytics/cash-flow        — Cash flow analysis
    GET  /api/v1/analytics/sales/summary    — Sales summary
    GET  /api/v1/analytics/sales/periods    — Sales period comparison
    GET  /api/v1/analytics/sales/top-customers — Top customers
    GET  /api/v1/analytics/purchases/summary — Purchase summary
    GET  /api/v1/analytics/purchases/top-suppliers — Top suppliers
    GET  /api/v1/analytics/inventory        — Inventory summary
    GET  /api/v1/analytics/inventory/movements — Stock movements
    GET  /api/v1/analytics/projects         — Project portfolio
    GET  /api/v1/analytics/projects/costs   — Project cost breakdown
    GET  /api/v1/analytics/hr               — HR summary
    GET  /api/v1/analytics/alerts           — Business alerts
    GET  /api/v1/analytics/dashboard/{role} — Role-based dashboard
    GET  /api/v1/analytics/drill-down/{type}/{id} — Drill-down to source
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from core.analytics_engine import (
    get_executive_summary, get_kpis, get_revenue_trend, get_expenses_trend,
    get_profit_trend, get_cash_flow, get_sales_summary, get_sales_by_period,
    get_top_customers, get_purchase_summary, get_top_suppliers,
    get_inventory_summary, get_stock_movements, get_project_summary,
    get_project_cost_breakdown, get_hr_summary, get_business_alerts,
    get_dashboard_for_role, drill_down
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/executive")
async def executive_summary(
    user: dict = Depends(get_current_user),
    period: str = Query("this_month", description="Period: today/yesterday/this_week/last_week/this_month/last_month/this_quarter/last_quarter/this_year/last_year")
):
    return get_executive_summary(user["tenant_id"], period)


@router.get("/kpis")
async def kpis(
    user: dict = Depends(get_current_user),
    period: str = Query("this_month", description="Period")
):
    return {"kpis": get_kpis(user["tenant_id"], period)}


@router.get("/revenue-trend")
async def revenue_trend(
    user: dict = Depends(get_current_user),
    months: int = Query(12, ge=1, le=36, description="Number of months")
):
    return {"trend": get_revenue_trend(user["tenant_id"], months)}


@router.get("/expenses-trend")
async def expenses_trend(
    user: dict = Depends(get_current_user),
    months: int = Query(12, ge=1, le=36, description="Number of months")
):
    return {"trend": get_expenses_trend(user["tenant_id"], months)}


@router.get("/profit-trend")
async def profit_trend(
    user: dict = Depends(get_current_user),
    months: int = Query(12, ge=1, le=36, description="Number of months")
):
    return {"trend": get_profit_trend(user["tenant_id"], months)}


@router.get("/cash-flow")
async def cash_flow(
    user: dict = Depends(get_current_user),
    months: int = Query(6, ge=1, le=24, description="Number of months")
):
    return {"cash_flow": get_cash_flow(user["tenant_id"], months)}


@router.get("/sales/summary")
async def sales_summary(
    user: dict = Depends(get_current_user),
    period: str = Query("this_month")
):
    return get_sales_summary(user["tenant_id"], period)


@router.get("/sales/periods")
async def sales_periods(user: dict = Depends(get_current_user)):
    return get_sales_by_period(user["tenant_id"])


@router.get("/sales/top-customers")
async def top_customers(
    user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50)
):
    return {"customers": get_top_customers(user["tenant_id"], limit)}


@router.get("/purchases/summary")
async def purchase_summary(
    user: dict = Depends(get_current_user),
    period: str = Query("this_month")
):
    return get_purchase_summary(user["tenant_id"], period)


@router.get("/purchases/top-suppliers")
async def top_suppliers(
    user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50)
):
    return {"suppliers": get_top_suppliers(user["tenant_id"], limit)}


@router.get("/inventory")
async def inventory_summary(user: dict = Depends(get_current_user)):
    return get_inventory_summary(user["tenant_id"])


@router.get("/inventory/movements")
async def inventory_movements(
    user: dict = Depends(get_current_user),
    days: int = Query(30, ge=1, le=90)
):
    return {"movements": get_stock_movements(user["tenant_id"], days)}


@router.get("/projects")
async def project_summary(user: dict = Depends(get_current_user)):
    return get_project_summary(user["tenant_id"])


@router.get("/projects/costs")
async def project_costs(user: dict = Depends(get_current_user)):
    return {"projects": get_project_cost_breakdown(user["tenant_id"])}


@router.get("/hr")
async def hr_summary(user: dict = Depends(get_current_user)):
    return get_hr_summary(user["tenant_id"])


@router.get("/alerts")
async def business_alerts(user: dict = Depends(get_current_user)):
    return {"alerts": get_business_alerts(user["tenant_id"])}


@router.get("/dashboard/{role}")
async def role_dashboard(
    role: str,
    user: dict = Depends(get_current_user),
    period: str = Query("this_month")
):
    valid_roles = ["owner", "ceo", "admin", "finance", "project_manager", "procurement", "warehouse"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    return get_dashboard_for_role(user["tenant_id"], role, period)


@router.get("/drill-down/{entity_type}/{entity_id}")
async def drill_down_endpoint(
    entity_type: str,
    entity_id: str,
    user: dict = Depends(get_current_user)
):
    valid_types = ["invoice", "purchase_order", "project", "payment"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}")
    result = drill_down(user["tenant_id"], entity_type, entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result