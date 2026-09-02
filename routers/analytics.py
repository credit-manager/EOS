from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.analytics_engine import AnalyticsEngine
from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/analytics", tags=["Analytics & Pipelines"])


# ------------------------------------------------ dashboards
@router.get("/dashboards",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_dashboards(dashboard_type: str | None = None,
                         user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).list_dashboards(user["tenant_id"], dashboard_type=dashboard_type)
    return {"status": "success", "data": data}


@router.post("/dashboards",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_dashboard(body: dict,
                         user: dict | None=None, db: Session = Depends(get_db)):
    required = ["dashboard_name", "dashboard_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    did = AnalyticsEngine(db).create_dashboard(
        user["tenant_id"], body["dashboard_name"], body["dashboard_type"],
        layout_config=body.get("layout_config"),
        is_shared=body.get("is_shared", False),
        owner_id=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": did, "message": "Dashboard created"}}


@router.get("/dashboards/{dashboard_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_dashboard(dashboard_id: str,
                      user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).get_dashboard(user["tenant_id"], dashboard_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Dashboard not found"}})
    return {"status": "success", "data": data}


@router.delete("/dashboards/{dashboard_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_dashboard(dashboard_id: str,
                         user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).delete_dashboard(user["tenant_id"], dashboard_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Dashboard not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}


# -------------------------------------------------- widgets
@router.get("/dashboards/{dashboard_id}/widgets",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_widgets(dashboard_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).list_widgets(dashboard_id)
    return {"status": "success", "data": data}


@router.post("/dashboards/{dashboard_id}/widgets",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_widget(dashboard_id: str, body: dict,
                      user: dict | None=None, db: Session = Depends(get_db)):
    if "widget_type" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "widget_type required"}})
    wid = AnalyticsEngine(db).create_widget(
        dashboard_id, body["widget_type"],
        title=body.get("title"), config=body.get("config"),
        position_x=body.get("position_x", 0),
        position_y=body.get("position_y", 0),
        width=body.get("width", 6), height=body.get("height", 4))
    db.commit()
    return {"status": "success", "data": {"id": wid, "message": "Widget created"}}


@router.delete("/widgets/{widget_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_widget(widget_id: str,
                      user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).delete_widget(widget_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Widget not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}


# ------------------------------------------------ pipelines
@router.get("/pipelines",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_pipelines(status: str | None = None,
                        user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).list_pipelines(user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/pipelines",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_pipeline(body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    required = ["pipeline_name", "source_type", "target_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = AnalyticsEngine(db).create_pipeline(
        user["tenant_id"], body["pipeline_name"], body["source_type"],
        body["target_type"], config=body.get("config"),
        schedule=body.get("schedule"))
    db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Pipeline created"}}


@router.get("/pipelines/{pipeline_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_pipeline(pipeline_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).get_pipeline(user["tenant_id"], pipeline_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Pipeline not found"}})
    return {"status": "success", "data": data}


@router.put("/pipelines/{pipeline_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_pipeline(pipeline_id: str, body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).update_pipeline(user["tenant_id"], pipeline_id, **body)
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------- pipeline runs
@router.get("/pipeline-runs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_pipeline_runs(pipeline_id: str | None = None, status: str | None = None, limit: int = 20,
                            user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).list_pipeline_runs(
        user["tenant_id"], pipeline_id=pipeline_id, status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/pipeline-runs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_pipeline_run(body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    if "pipeline_id" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "pipeline_id required"}})
    rid = AnalyticsEngine(db).create_pipeline_run(
        body["pipeline_id"], user["tenant_id"])
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Pipeline run started"}}


@router.put("/pipeline-runs/{run_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def complete_pipeline_run(run_id: str, body: dict,
                             user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).complete_pipeline_run(
        run_id,
        records_processed=body.get("records_processed", 0),
        records_failed=body.get("records_failed", 0),
        error_message=body.get("error_message"))
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------ analytics alerts
@router.get("/alerts",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_alerts(is_active: bool | None = None,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = AnalyticsEngine(db).list_alerts(user["tenant_id"], is_active=is_active)
    return {"status": "success", "data": data}


@router.post("/alerts",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_alert(body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    required = ["alert_name", "metric_name", "condition", "threshold_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    aid = AnalyticsEngine(db).create_alert(
        user["tenant_id"], body["alert_name"], body["metric_name"],
        body["condition"], body["threshold_value"],
        notification_channels=body.get("notification_channels"))
    db.commit()
    return {"status": "success", "data": {"id": aid, "message": "Alert created"}}


@router.put("/alerts/{alert_id}/trigger",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def trigger_alert(alert_id: str,
                       user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).trigger_alert(user["tenant_id"], alert_id)
    db.commit()
    return {"status": "success", "data": result}


@router.delete("/alerts/{alert_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_alert(alert_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    result = AnalyticsEngine(db).delete_alert(user["tenant_id"], alert_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Alert not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}
