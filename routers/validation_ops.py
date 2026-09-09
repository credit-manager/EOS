from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.validation_ops import ProductionValidationEngine

router = APIRouter(prefix="/api/v1/dynamic/ops", tags=["Production Validation"])


# -------------------------------------------------------- validation rules
@router.get("/validation-rules",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_validation_rules(rule_type: str = None,
                               user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_validation_rules(
        user["tenant_id"], rule_type=rule_type)
    return {"status": "success", "data": data}


@router.post("/validation-rules",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_validation_rule(body: dict,
                                user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["rule_name", "rule_type", "check_command"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = ProductionValidationEngine(db).create_validation_rule(
        user["tenant_id"], body["rule_name"], body["rule_type"], body["check_command"],
        expected_value=body.get("expected_value"), severity=body.get("severity", "error"))
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Validation rule created"}}


@router.get("/validation-rules/{rule_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_validation_rule(rule_id: str,
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).get_validation_rule(user["tenant_id"], rule_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Validation rule not found"}})
    return {"status": "success", "data": data}


@router.put("/validation-rules/{rule_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_validation_rule(rule_id: str, body: dict,
                                user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionValidationEngine(db).update_validation_rule(
        user["tenant_id"], rule_id,
        is_active=body.get("is_active"), severity=body.get("severity"),
        check_command=body.get("check_command"))
    db.commit()
    return {"status": "success", "data": result}


# ------------------------------------------------------ validation results
@router.get("/validation-results",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_validation_results(check_type: str = None, status: str = None, limit: int = 50,
                                 user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_validation_results(
        user["tenant_id"], check_type=check_type, status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/validation-results",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_validation_result(body: dict,
                                  user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["check_type", "status"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    vid = ProductionValidationEngine(db).record_validation_result(
        user["tenant_id"], body["check_type"], body["status"],
        rule_id=body.get("rule_id"), rule_name=body.get("rule_name"),
        actual_value=body.get("actual_value"), expected_value=body.get("expected_value"),
        message=body.get("message"), execution_time_ms=body.get("execution_time_ms"))
    db.commit()
    return {"status": "success", "data": {"id": vid, "message": "Validation result recorded"}}


# ----------------------------------------------------------- health checks
@router.get("/health-checks",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_health_checks(check_type: str = None, status: str = None,
                            user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_health_checks(
        user["tenant_id"], check_type=check_type, status=status)
    return {"status": "success", "data": data}


@router.post("/health-checks",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_health_check(body: dict,
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["check_name", "check_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    hid = ProductionValidationEngine(db).create_health_check(
        user["tenant_id"], body["check_name"], body["check_type"],
        target=body.get("target"))
    db.commit()
    return {"status": "success", "data": {"id": hid, "message": "Health check created"}}


@router.get("/health-checks/{check_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_health_check(check_id: str,
                          user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).get_health_check(user["tenant_id"], check_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Health check not found"}})
    return {"status": "success", "data": data}


@router.put("/health-checks/{check_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_health_check(check_id: str, body: dict,
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionValidationEngine(db).update_health_check(
        user["tenant_id"], check_id, body.get("status", "healthy"),
        response_time_ms=body.get("response_time_ms"),
        message=body.get("message"))
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------------- ssl certificates
@router.get("/ssl-certificates",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_ssl_certificates(domain: str = None, status: str = None,
                               user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_ssl_certificates(
        user["tenant_id"], domain=domain, status=status)
    return {"status": "success", "data": data}


@router.post("/ssl-certificates",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def register_ssl_certificate(body: dict,
                                  user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["domain"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    sid = ProductionValidationEngine(db).register_ssl_certificate(
        user["tenant_id"], body["domain"],
        issuer=body.get("issuer"), serial_number=body.get("serial_number"),
        not_before=body.get("not_before"), not_after=body.get("not_after"),
        auto_renew=body.get("auto_renew", True))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "SSL certificate registered"}}


@router.get("/ssl-certificates/{cert_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_ssl_certificate(cert_id: str,
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).get_ssl_certificate(user["tenant_id"], cert_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "SSL certificate not found"}})
    return {"status": "success", "data": data}


@router.put("/ssl-certificates/{cert_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_ssl_certificate(cert_id: str, body: dict,
                                user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionValidationEngine(db).update_ssl_certificate(
        user["tenant_id"], cert_id,
        status=body.get("status"), not_after=body.get("not_after"))
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------- environment configs
@router.get("/env-configs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_env_configs(environment: str = None,
                          user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_environment_configs(
        user["tenant_id"], environment=environment)
    return {"status": "success", "data": data}


@router.post("/env-configs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def set_env_config(body: dict,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["environment", "config_key", "config_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eid = ProductionValidationEngine(db).set_environment_config(
        user["tenant_id"], body["environment"], body["config_key"], body["config_value"],
        is_sensitive=body.get("is_sensitive", False),
        description=body.get("description"))
    db.commit()
    return {"status": "success", "data": {"id": eid, "message": "Environment config saved"}}


@router.delete("/env-configs/{config_id}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_env_config(config_id: str,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionValidationEngine(db).delete_environment_config(
        user["tenant_id"], config_id)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Environment config not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}


# --------------------------------------------------------- security scans
@router.get("/security-scans",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_security_scans(scan_type: str = None, status: str = None,
                             user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).list_security_scans(
        user["tenant_id"], scan_type=scan_type, status=status)
    return {"status": "success", "data": data}


@router.post("/security-scans",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_security_scan(body: dict,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    required = ["scan_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    sid = ProductionValidationEngine(db).create_security_scan(
        user["tenant_id"], body["scan_type"], target=body.get("target"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Security scan started"}}


@router.get("/security-scans/{scan_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_security_scan(scan_id: str,
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ProductionValidationEngine(db).get_security_scan(user["tenant_id"], scan_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Security scan not found"}})
    return {"status": "success", "data": data}


@router.put("/security-scans/{scan_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_security_scan(scan_id: str, body: dict,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProductionValidationEngine(db).update_security_scan(
        user["tenant_id"], scan_id, body.get("status", "completed"),
        vulnerabilities_found=body.get("vulnerabilities_found"),
        critical_count=body.get("critical_count"),
        high_count=body.get("high_count"),
        medium_count=body.get("medium_count"),
        low_count=body.get("low_count"),
        report_url=body.get("report_url"))
    db.commit()
    return {"status": "success", "data": result}
