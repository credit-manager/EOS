from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.compliance_engine import ComplianceEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/compliance", tags=["Compliance & Policy"])


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(401, detail="Authenticated tenant is required")
    return tenant_id


@router.get("/policies", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_policies(is_active: bool | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ComplianceEngine(db).list_policies(_tenant(user), is_active=is_active)}


@router.post("/policies", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_policy(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["policy_name", "policy_type", "rules_config"]:
        if f not in body: raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = ComplianceEngine(db).create_policy(_tenant(user), body["policy_name"], body["policy_type"], body["rules_config"], description=body.get("description"), severity=body.get("severity", "medium")); db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Policy created"}}


@router.get("/policies/{policy_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_policy(policy_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    data = ComplianceEngine(db).get_policy(_tenant(user), policy_id)
    if not data: raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Policy not found"}})
    return {"status": "success", "data": data}


@router.put("/policies/{policy_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_policy(policy_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try: result = ComplianceEngine(db).update_policy(_tenant(user), policy_id, **body)
    except ValueError as exc: raise HTTPException(400, detail=str(exc)) from exc
    db.commit(); return {"status": "success", "data": result}


@router.delete("/policies/{policy_id}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_policy(policy_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ComplianceEngine(db).delete_policy(_tenant(user), policy_id)
    if not result: raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found"}})
    db.commit(); return {"status": "success", "data": {"deleted": True}}


@router.get("/checks", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_checks(policy_id: str | None = None, status: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ComplianceEngine(db).list_checks(_tenant(user), policy_id=policy_id, status=status)}


@router.post("/checks", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_check(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["policy_id", "check_name", "check_type"]:
        if f not in body: raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try: cid = ComplianceEngine(db).create_check(_tenant(user), body["policy_id"], body["check_name"], body["check_type"], target_entity=body.get("target_entity"))
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    db.commit(); return {"status": "success", "data": {"id": cid, "message": "Check created"}}


@router.put("/checks/{check_id}/run", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def run_check(check_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try: result = ComplianceEngine(db).run_check(_tenant(user), check_id, body.get("status", "passed"), result_detail=body.get("result_detail"))
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    db.commit(); return {"status": "success", "data": result}


@router.get("/violations", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_violations(status: str | None = None, severity: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ComplianceEngine(db).list_violations(_tenant(user), status=status, severity=severity)}


@router.post("/violations", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_violation(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["policy_id", "violation_type", "severity"]:
        if f not in body: raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try: vid = ComplianceEngine(db).create_violation(_tenant(user), body["policy_id"], body["violation_type"], body["severity"], entity_type=body.get("entity_type"), entity_id=body.get("entity_id"), description=body.get("description"), check_id=body.get("check_id"), assigned_to=body.get("assigned_to"))
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    db.commit(); return {"status": "success", "data": {"id": vid, "message": "Violation created"}}


@router.put("/violations/{violation_id}/resolve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def resolve_violation(violation_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try: result = ComplianceEngine(db).resolve_violation(_tenant(user), violation_id)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    db.commit(); return {"status": "success", "data": result}


@router.get("/audit-log", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_audit_log(action: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ComplianceEngine(db).list_audit_log(_tenant(user), action=action)}


@router.post("/audit-log", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def log_action(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "action" not in body: raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "action required"}})
    lid = ComplianceEngine(db).log_action(_tenant(user), body["action"], entity_type=body.get("entity_type"), entity_id=body.get("entity_id"), actor_id=user.get("id"), details=body.get("details")); db.commit()
    return {"status": "success", "data": {"id": lid, "message": "Audit logged"}}


@router.get("/frameworks", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_frameworks(framework_type: str | None = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ComplianceEngine(db).list_frameworks(_tenant(user), framework_type=framework_type)}


@router.post("/frameworks", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_framework(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["framework_name", "framework_type"]:
        if f not in body: raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    fid = ComplianceEngine(db).create_framework(_tenant(user), body["framework_name"], body["framework_type"], requirements=body.get("requirements"), version=body.get("version")); db.commit()
    return {"status": "success", "data": {"id": fid, "message": "Framework created"}}