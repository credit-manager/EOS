"""
P31 Audit & Compliance Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.audit_engine import AuditComplianceEngine
from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Audit & Compliance"])


@router.get("/companies/{cid}/audit-trail", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_audit_trail(cid: str, entity_type: str | None = None, entity_id: str | None = None,
                          actor_id: str | None = None, from_date: str | None = None,
                          to_date: str | None = None, user: dict | None=None,
                          db: Session = Depends(get_db)):
    return {"status": "success", "data": AuditComplianceEngine(db).get_audit_trail(
        cid, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id,
        from_date=from_date, to_date=to_date, tenant_id=user.get("tenant_id"))}


@router.get("/companies/{cid}/audit-trail/entity/{entity_type}/{entity_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_entity_history(cid: str, entity_type: str, entity_id: str, db: Session=None):
    return {"status": "success", "data": AuditComplianceEngine(db).get_entity_history(cid, entity_type, entity_id)}


@router.get("/companies/{cid}/access-logs", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_access_logs(cid: str, user_id: str | None = None, resource_type: str | None = None,
                          user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AuditComplianceEngine(db).get_access_logs(
        tenant_id=user.get("tenant_id"), user_id=user_id, resource_type=resource_type)}


@router.post("/companies/{cid}/access-logs", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def log_access(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("user_id", "action", "resource_type"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = AuditComplianceEngine(db).log_access(user.get("tenant_id"), body["user_id"],
                                                body.get("user_email"), body["action"],
                                                body["resource_type"], body.get("resource_id"),
                                                access_granted=body.get("access_granted", True),
                                                denial_reason=body.get("denial_reason"),
                                                ip_address=body.get("ip_address"))
    db.commit()
    return {"status": "success", "data": {"id": lid}}


@router.get("/companies/{cid}/compliance-rules", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_compliance_rules(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AuditComplianceEngine(db).list_compliance_rules(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/compliance-rules", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_compliance_rule(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("rule_code", "name", "entity_type"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = AuditComplianceEngine(db).create_compliance_rule(user.get("tenant_id"), cid,
                                                            body["rule_code"], body["name"],
                                                            body["entity_type"],
                                                            description=body.get("description"),
                                                            category=body.get("category"),
                                                            severity=body.get("severity", "medium"),
                                                            rule_expression=body.get("rule_expression"))
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.put("/compliance-rules/{rid}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_compliance_rule(rid: str, body: dict, db: Session=None):
    result = AuditComplianceEngine(db).update_compliance_rule(rid, **body)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UPDATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/compliance-check", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def compliance_check(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AuditComplianceEngine(db).run_compliance_check(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/audit-exports", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_audit_export(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("export_type", "from_date", "to_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    xid = AuditComplianceEngine(db).create_audit_export(user.get("tenant_id"), cid,
                                                         body["export_type"], body["from_date"],
                                                         body["to_date"],
                                                         entity_types=body.get("entity_types"),
                                                         exported_by=user.get("id"))
    db.commit()
    return {"status": "success", "data": {"id": xid}}


@router.get("/companies/{cid}/audit-exports", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_audit_exports(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AuditComplianceEngine(db).list_audit_exports(cid, tenant_id=user.get("tenant_id"))}
