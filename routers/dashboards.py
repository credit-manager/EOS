"""
P16 Dashboard / Analytics Router — CRUD + execute + KPI
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import uuid

from database import get_db
from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from core.analytics_engine import AnalyticsEngine


router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Dashboard / Analytics"]
)


# ──────────────────────────────────────────────────────────────
# DASHBOARD CRUD
# ──────────────────────────────────────────────────────────────

@router.get(
    "/dashboards",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_dashboards(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List dashboards visible to the current user."""
    tenant_id = user.get("tenant_id")
    user_roles = user.get("roles", [])

    conditions = ["is_active = true"]
    params: dict = {}

    if tenant_id:
        conditions.append("(tenant_id = :tid OR tenant_id IS NULL)")
        params["tid"] = tenant_id

    where = " AND ".join(conditions)
    rows = db.execute(
        text(
            f"SELECT id, code, name_en, name_ar, description, is_default, "
            f"owner_user_id, allowed_roles, created_at "
            f"FROM dbp_dashboards WHERE {where} ORDER BY is_default DESC, name_en"
        ),
        params,
    ).fetchall()

    dashboards = []
    for r in rows:
        allowed = r[7] if isinstance(r[7], list) else []
        # Filter by role if allowed_roles is set
        if allowed and not any(role in allowed for role in user_roles):
            if "*" not in allowed:
                continue
        dashboards.append({
            "id": r[0],
            "code": r[1],
            "name_en": r[2],
            "name_ar": r[3],
            "description": r[4],
            "is_default": bool(r[5]),
            "owner_user_id": r[6],
            "allowed_roles": allowed,
            "created_at": r[8].isoformat() if r[8] else None,
        })

    return {"status": "success", "data": dashboards}


@router.post(
    "/dashboards",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_dashboard(
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new dashboard."""
    tenant_id = user.get("tenant_id")
    user_id = user.get("id") or user.get("user_id")

    code = body.get("code")
    name_en = body.get("name_en")
    if not code or not name_en:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING_FIELDS", "message": "code and name_en required"},
        })

    # Check unique code
    existing = db.execute(
        text("SELECT id FROM dbp_dashboards WHERE code = :code"),
        {"code": code},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "DUPLICATE", "message": f"Dashboard '{code}' already exists"},
        })

    dash_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO dbp_dashboards "
            "(id, tenant_id, code, name_en, name_ar, description, "
            "layout, is_active, is_default, owner_user_id, allowed_roles) "
            "VALUES (:id, :tid, :code, :name_en, :name_ar, :desc, "
            "'{}', true, false, :owner, :roles)"
        ),
        {
            "id": dash_id,
            "tid": tenant_id,
            "code": code,
            "name_en": name_en,
            "name_ar": body.get("name_ar"),
            "desc": body.get("description"),
            "owner": user_id,
            "roles": json_dumps(body.get("allowed_roles", [])),
        },
    )
    db.commit()

    return {"status": "success", "data": {"id": dash_id, "code": code}}


@router.get(
    "/dashboards/{dashboard_id}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """Get dashboard with all widgets."""
    engine = AnalyticsEngine(db)
    result = engine.execute_dashboard(dashboard_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": result["error"]},
        })

    return {"status": "success", "data": result}


@router.delete(
    "/dashboards/{dashboard_id}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """Delete a dashboard and its widgets."""
    result = db.execute(
        text("DELETE FROM dbp_dashboards WHERE id = :id"),
        {"id": dashboard_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Dashboard not found"},
        })

    return {"status": "success", "message": "Dashboard deleted"}


# ──────────────────────────────────────────────────────────────
# WIDGET CRUD
# ──────────────────────────────────────────────────────────────

@router.post(
    "/dashboards/{dashboard_id}/widgets",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_widget(
    dashboard_id: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """Add a widget to a dashboard."""
    # Validate dashboard exists
    dash = db.execute(
        text("SELECT id FROM dbp_dashboards WHERE id = :id"),
        {"id": dashboard_id},
    ).fetchone()
    if not dash:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Dashboard not found"},
        })

    code = body.get("code")
    entity_code = body.get("entity_code")
    title = body.get("title")
    widget_type = body.get("widget_type", "kpi")

    if not code or not entity_code or not title:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING_FIELDS", "message": "code, entity_code, title required"},
        })

    if widget_type not in ALLOWED_WIDGET_TYPES_IMPORT:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "INVALID_TYPE",
                       "message": f"widget_type must be one of: {ALLOWED_WIDGET_TYPES_IMPORT}"},
        })

    # Validate entity exists
    from core.analytics_engine import AnalyticsEngine
    engine = AnalyticsEngine(db)
    if not engine._validate_entity(entity_code):
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "INVALID_ENTITY", "message": f"Entity '{entity_code}' not found"},
        })

    widget_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO dbp_dashboard_widgets "
            "(id, dashboard_id, code, widget_type, title, title_ar, "
            "entity_code, position_x, position_y, width, height, "
            "query_config, style_config, is_active) "
            "VALUES (:id, :did, :code, :wt, :title, :title_ar, "
            ":ec, :px, :py, :w, :h, :qc, :sc, true)"
        ),
        {
            "id": widget_id,
            "did": dashboard_id,
            "code": code,
            "wt": widget_type,
            "title": title,
            "title_ar": body.get("title_ar"),
            "ec": entity_code,
            "px": body.get("position_x", 0),
            "py": body.get("position_y", 0),
            "w": body.get("width", 1),
            "h": body.get("height", 1),
            "qc": json_dumps(body.get("query_config", {})),
            "sc": json_dumps(body.get("style_config", {})),
        },
    )
    db.commit()

    return {"status": "success", "data": {"id": widget_id, "code": code}}


@router.get(
    "/dashboards/{dashboard_id}/widgets",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_widgets(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """List widgets for a dashboard."""
    rows = db.execute(
        text(
            "SELECT id, code, widget_type, title, title_ar, entity_code, "
            "position_x, position_y, width, height, query_config "
            "FROM dbp_dashboard_widgets "
            "WHERE dashboard_id = :did AND is_active = true "
            "ORDER BY position_y, position_x"
        ),
        {"did": dashboard_id},
    ).fetchall()

    widgets = [
        {
            "id": r[0], "code": r[1], "widget_type": r[2],
            "title": r[3], "title_ar": r[4], "entity_code": r[5],
            "position": {"x": r[6], "y": r[7], "width": r[8], "height": r[9]},
            "query_config": r[10],
        }
        for r in rows
    ]

    return {"status": "success", "data": widgets}


@router.delete(
    "/dashboards/{dashboard_id}/widgets/{widget_id}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    db: Session = Depends(get_db),
):
    """Delete a widget from a dashboard."""
    result = db.execute(
        text("DELETE FROM dbp_dashboard_widgets WHERE id = :id AND dashboard_id = :did"),
        {"id": widget_id, "did": dashboard_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Widget not found"},
        })

    return {"status": "success", "message": "Widget deleted"}


# ──────────────────────────────────────────────────────────────
# KPI CRUD
# ──────────────────────────────────────────────────────────────

@router.get(
    "/kpis",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_kpis(
    db: Session = Depends(get_db),
):
    """List all KPI definitions."""
    rows = db.execute(
        text(
            "SELECT id, code, name_en, name_ar, entity_code, "
            "aggregation, column_name, group_by, date_field, "
            "date_range, format_type, is_active "
            "FROM dbp_kpis ORDER BY code"
        ),
    ).fetchall()

    kpis = [
        {
            "id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
            "entity_code": r[4], "aggregation": r[5], "column_name": r[6],
            "group_by": r[7], "date_field": r[8], "date_range": r[9],
            "format_type": r[10], "is_active": bool(r[11]),
        }
        for r in rows
    ]

    return {"status": "success", "data": kpis}


@router.post(
    "/kpis",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_kpi(
    body: dict,
    db: Session = Depends(get_db),
):
    """Create a KPI definition."""
    code = body.get("code")
    name_en = body.get("name_en")
    entity_code = body.get("entity_code")
    aggregation = body.get("aggregation", "COUNT").upper()

    if not code or not name_en or not entity_code:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING_FIELDS", "message": "code, name_en, entity_code required"},
        })

    if aggregation not in ALLOWED_AGGREGATIONS_IMPORT:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "INVALID_AGG",
                       "message": f"aggregation must be one of: {ALLOWED_AGGREGATIONS_IMPORT}"},
        })

    kpi_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO dbp_kpis "
            "(id, tenant_id, code, name_en, name_ar, entity_code, "
            "aggregation, column_name, filters, group_by, "
            "date_field, date_range, format_type, is_active) "
            "VALUES (:id, NULL, :code, :name_en, :name_ar, :ec, "
            ":agg, :col, :filters, :gb, :df, :dr, :fmt, true)"
        ),
        {
            "id": kpi_id,
            "code": code,
            "name_en": name_en,
            "name_ar": body.get("name_ar"),
            "ec": entity_code,
            "agg": aggregation,
            "col": body.get("column_name"),
            "filters": json_dumps(body.get("filters", [])),
            "gb": body.get("group_by"),
            "df": body.get("date_field"),
            "dr": body.get("date_range"),
            "fmt": body.get("format_type", "number"),
        },
    )
    db.commit()

    return {"status": "success", "data": {"id": kpi_id, "code": code}}


@router.get(
    "/kpis/{kpi_id}/execute",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def execute_kpi(
    kpi_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a KPI and return the result."""
    tenant_id = user.get("tenant_id")
    engine = AnalyticsEngine(db)
    result = engine.execute_kpi(kpi_id, tenant_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "KPI_ERROR", "message": result["error"]},
        })

    return {"status": "success", "data": result}


@router.delete(
    "/kpis/{kpi_id}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_kpi(
    kpi_id: str,
    db: Session = Depends(get_db),
):
    """Delete a KPI definition."""
    result = db.execute(
        text("DELETE FROM dbp_kpis WHERE id = :id"),
        {"id": kpi_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "KPI not found"},
        })

    return {"status": "success", "message": "KPI deleted"}


# ──────────────────────────────────────────────────────────────
# AD-HOC AGGREGATION
# ──────────────────────────────────────────────────────────────

@router.post(
    "/analytics/aggregate",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def run_aggregation(
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run an ad-hoc aggregation query."""
    tenant_id = user.get("tenant_id")
    engine = AnalyticsEngine(db)

    result = engine.execute_aggregation(
        entity_code=body.get("entity_code", ""),
        aggregation=body.get("aggregation", "COUNT"),
        column_name=body.get("column_name"),
        filters=body.get("filters"),
        group_by=body.get("group_by"),
        date_field=body.get("date_field"),
        date_range=body.get("date_range"),
        tenant_id=tenant_id,
        limit=body.get("limit", 100),
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "AGGREGATION_ERROR", "message": result["error"]},
        })

    return {"status": "success", "data": result}


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

import json

ALLOWED_WIDGET_TYPES_IMPORT = {"kpi", "table", "bar_chart", "line_chart", "pie_chart", "summary"}
ALLOWED_AGGREGATIONS_IMPORT = {"COUNT", "SUM", "AVG", "MIN", "MAX"}


def json_dumps(obj):
    """Safe JSON dumps."""
    if obj is None:
        return "{}"
    return json.dumps(obj)
