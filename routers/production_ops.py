from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.production_ops import ProductionOpsEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Production Operations"])


# -------------------------------------------------------------- backup jobs
@router.get("/backup-jobs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_backup_jobs(backup_type: str = None, status: str = None, limit: int = 50,
                          user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_backup_jobs(
        user["tenant_id"], backup_type=backup_type, status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/backup-jobs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_backup_job(body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["backup_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    bid = ProductionOpsEngine(db).create_backup_job(
        user["tenant_id"], body.get("company_id"), body["backup_type"],
        target_tables=body.get("target_tables"),
        created_by=user.get("user_id"))
    db.commit()
    return {"status": "success", "data": {"id": bid, "message": "Backup job created"}}


@router.get("/backup-jobs/{backup_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_backup_job(backup_id: str,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).get_backup_job(user["tenant_id"], backup_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Backup job not found"}})
    return {"status": "success", "data": data}


@router.put("/backup-jobs/{backup_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_backup_job(backup_id: str, body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).update_backup_status(
        user["tenant_id"], backup_id, body.get("status", "running"),
        file_path=body.get("file_path"), file_size_bytes=body.get("file_size_bytes"),
        checksum=body.get("checksum"), error_message=body.get("error_message"))
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Backup job not found"}})
    db.commit()
    return {"status": "success", "data": result}


# ----------------------------------------------------------- scheduled jobs
@router.get("/scheduled-jobs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_scheduled_jobs(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_scheduled_jobs(user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/scheduled-jobs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_scheduled_job(body: dict,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["job_name", "job_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    jid = ProductionOpsEngine(db).create_scheduled_job(
        user["tenant_id"], body["job_name"], body["job_type"],
        cron_expression=body.get("cron_expression"),
        interval_seconds=body.get("interval_seconds"),
        payload=body.get("payload"))
    db.commit()
    return {"status": "success", "data": {"id": jid, "message": "Scheduled job created"}}


@router.get("/scheduled-jobs/{job_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_scheduled_job(job_id: str,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).get_scheduled_job(user["tenant_id"], job_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Scheduled job not found"}})
    return {"status": "success", "data": data}


@router.put("/scheduled-jobs/{job_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_scheduled_job(job_id: str, body: dict,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).update_scheduled_job(
        user["tenant_id"], job_id,
        is_active=body.get("is_active"),
        cron_expression=body.get("cron_expression"),
        interval_seconds=body.get("interval_seconds"),
        payload=body.get("payload"))
    db.commit()
    return {"status": "success", "data": result}


@router.delete("/scheduled-jobs/{job_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_scheduled_job(job_id: str,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).delete_scheduled_job(user["tenant_id"], job_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Scheduled job not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}


# ------------------------------------------------------------ alert rules
@router.get("/alert-rules",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_alert_rules(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_alert_rules(user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/alert-rules",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_alert_rule(body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["rule_name", "metric_name", "condition_op", "threshold_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = ProductionOpsEngine(db).create_alert_rule(
        user["tenant_id"], body["rule_name"], body["metric_name"],
        body["condition_op"], body["threshold_value"],
        company_id=body.get("company_id"),
        severity=body.get("severity", "warning"),
        notification_channels=body.get("notification_channels"),
        cooldown_minutes=body.get("cooldown_minutes", 5))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Alert rule created"}}


@router.get("/alert-rules/{rule_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_alert_rule(rule_id: str,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).get_alert_rule(user["tenant_id"], rule_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Alert rule not found"}})
    return {"status": "success", "data": data}


@router.put("/alert-rules/{rule_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_alert_rule(rule_id: str, body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).update_alert_rule(
        user["tenant_id"], rule_id,
        is_active=body.get("is_active"),
        threshold_value=body.get("threshold_value"),
        severity=body.get("severity"))
    db.commit()
    return {"status": "success", "data": result}


# ----------------------------------------------------------- alert history
@router.get("/alert-history",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_alert_history(status: str = None, severity: str = None, limit: int = 50,
                            user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_alert_history(
        user["tenant_id"], status=status, severity=severity, limit=limit)
    return {"status": "success", "data": data}


@router.post("/alert-history",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def trigger_alert(body: dict,
                       user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["rule_id", "rule_name", "metric_name", "actual_value", "threshold_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    aid = ProductionOpsEngine(db).trigger_alert(
        user["tenant_id"], body["rule_id"], body["rule_name"],
        body["metric_name"], body["actual_value"], body["threshold_value"],
        severity=body.get("severity", "warning"), message=body.get("message"))
    db.commit()
    return {"status": "success", "data": {"id": aid, "message": "Alert triggered"}}


@router.put("/alert-history/{alert_id}/acknowledge",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def acknowledge_alert(alert_id: str, body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).acknowledge_alert(
        user["tenant_id"], alert_id, body.get("acknowledged_by", user.get("user_id", "system")))
    db.commit()
    return {"status": "success", "data": result}


@router.put("/alert-history/{alert_id}/resolve",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def resolve_alert(alert_id: str,
                       user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).resolve_alert(user["tenant_id"], alert_id)
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------------- deployments
@router.get("/deployments",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_deployments(environment: str = None, status: str = None, limit: int = 20,
                          user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_deployments(
        user["tenant_id"], environment=environment, status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/deployments",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_deployment(body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["version", "environment"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    did = ProductionOpsEngine(db).create_deployment(
        user["tenant_id"], body["version"], body["environment"],
        deployed_by=user.get("user_id"),
        commit_sha=body.get("commit_sha"),
        release_notes=body.get("release_notes"))
    db.commit()
    return {"status": "success", "data": {"id": did, "message": "Deployment created"}}


@router.get("/deployments/{deployment_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_deployment(deployment_id: str,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).get_deployment(user["tenant_id"], deployment_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Deployment not found"}})
    return {"status": "success", "data": data}


@router.put("/deployments/{deployment_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_deployment(deployment_id: str, body: dict,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionOpsEngine(db).update_deployment_status(
        user["tenant_id"], deployment_id, body.get("status", "completed"),
        rollback_reason=body.get("rollback_reason"))
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------------- monitoring metrics
@router.get("/metrics",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_metrics(metric_name: str = None, source: str = None, limit: int = 100,
                      user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).list_metrics(
        user["tenant_id"], metric_name=metric_name, source=source, limit=limit)
    return {"status": "success", "data": data}


@router.post("/metrics",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_metric(body: dict,
                       user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["metric_name", "metric_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    mid = ProductionOpsEngine(db).record_metric(
        user["tenant_id"], body["metric_name"], body["metric_value"],
        unit=body.get("unit"), tags=body.get("tags"), source=body.get("source"))
    db.commit()
    return {"status": "success", "data": {"id": mid, "message": "Metric recorded"}}


@router.get("/metrics/{metric_name}/latest",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_latest_metric(metric_name: str,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionOpsEngine(db).get_latest_metric(user["tenant_id"], metric_name)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Metric not found"}})
    return {"status": "success", "data": data}
