from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.reporting_engine import ReportingEngine
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Business Intelligence"])


@router.get("/companies/{cid}/report-templates",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_templates(cid: str, report_type: str | None = None,
                        user: dict | None=None, db: Session = Depends(get_db)):
    data = ReportingEngine(db).list_report_templates(cid, tenant_id=user["tenant_id"], report_type=report_type)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/report-templates",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_template(cid: str, body: dict,
                         user: dict | None=None, db: Session = Depends(get_db)):
    if "name" not in body or "report_type" not in body or "data_source" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "name, report_type, data_source required"}})
    eng = ReportingEngine(db)
    tid = eng.create_report_template(
        user["tenant_id"], cid, body["name"], body["report_type"], body["data_source"],
        created_by=user.get("sub"),
        description=body.get("description"),
        parameters=body.get("parameters"),
        columns=body.get("columns"),
        filters=body.get("filters"),
        sort_config=body.get("sort_config"),
        is_public=body.get("is_public", False))
    db.commit()
    return {"status": "success", "data": {"id": tid, "message": "Template created"}}


@router.get("/report-templates/{tid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_template(tid: str, user: dict | None=None, db: Session = Depends(get_db)):
    tpl = ReportingEngine(db).get_report_template(tid)
    if not tpl:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Template not found"}})
    return {"status": "success", "data": tpl}


@router.put("/report-templates/{tid}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_template(tid: str, body: dict,
                         user: dict | None=None, db: Session = Depends(get_db)):
    eng = ReportingEngine(db)
    existing = eng.get_report_template(tid)
    if not existing:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Template not found"}})
    kw = {k: v for k, v in body.items() if v is not None}
    result = eng.update_report_template(tid, **kw)
    db.commit()
    return {"status": "success", "data": result}


@router.post("/report-templates/{tid}/run",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def run_report(tid: str, body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    eng = ReportingEngine(db)
    tpl = eng.get_report_template(tid)
    if not tpl:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Template not found"}})
    try:
        run_id = eng.run_report(
            user["tenant_id"], tpl["company_id"], tid,
            parameters=body.get("parameters"),
            format=body.get("format", "json"),
            created_by=user.get("sub"))
    except ValueError as e:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "BAD_REQUEST", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"run_id": run_id, "message": "Report started"}}


@router.get("/companies/{cid}/report-runs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_runs(cid: str, template_id: str | None = None,
                   user: dict | None=None, db: Session = Depends(get_db)):
    data = ReportingEngine(db).list_report_runs(cid, tenant_id=user["tenant_id"], template_id=template_id)
    return {"status": "success", "data": data}


@router.get("/report-runs/{rid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_run(rid: str, user: dict | None=None, db: Session = Depends(get_db)):
    run = ReportingEngine(db).get_report_run(rid)
    if not run:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Report run not found"}})
    return {"status": "success", "data": run}


@router.get("/companies/{cid}/scheduled-reports",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_scheduled(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    data = ReportingEngine(db).list_scheduled_reports(cid, tenant_id=user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/scheduled-reports",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_scheduled(cid: str, body: dict,
                          user: dict | None=None, db: Session = Depends(get_db)):
    required = ["template_id", "name", "schedule_cron", "recipients"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eng = ReportingEngine(db)
    sid = eng.create_scheduled_report(
        user["tenant_id"], cid, body["template_id"], body["name"],
        body["schedule_cron"], body["recipients"], body.get("format", "csv"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Scheduled report created"}}


@router.post("/scheduled-reports/{sid}/toggle",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def toggle_scheduled(sid: str, body: dict,
                          user: dict | None=None, db: Session = Depends(get_db)):
    if "is_active" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "is_active required"}})
    result = ReportingEngine(db).toggle_scheduled_report(sid, body["is_active"])
    db.commit()
    return {"status": "success", "data": result}
