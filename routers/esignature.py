"""
P33 E-Signature & Enhanced Approval Workflows Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.esignature_engine import ESignatureEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["E-Signature & Approvals"])


# ── Signature Requests ─────────────────────────────────────────

@router.get("/companies/{cid}/signature-requests",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_signature_requests(cid: str, status: str | None = None,
                                  user: dict | None=None,
                                  db: Session = Depends(get_db)):
    data = ESignatureEngine(db).list_signature_requests(
        cid, tenant_id=user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/signature-requests",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_signature_request(cid: str, body: dict,
                                   user: dict | None=None,
                                   db: Session = Depends(get_db)):
    if "title" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "title required"}})
    signers = body.get("signers", [])
    if not signers:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "signers required"}})
    rid = ESignatureEngine(db).create_signature_request(
        user["tenant_id"], cid, body["title"], signers,
        requested_by=user.get("user_id", "unknown"),
        description=body.get("description"),
        reference_type=body.get("reference_type"),
        reference_id=body.get("reference_id"))
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.get("/signature-requests/{rid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_signature_request(rid: str, db: Session=None):
    data = ESignatureEngine(db).get_signature_request(rid)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Signature request not found"}})
    return {"status": "success", "data": data}


@router.post("/signature-requests/{rid}/sign",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def sign_request(rid: str, body: dict, db: Session=None):
    for f in ("signer_id", "signature_data"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    result = ESignatureEngine(db).sign(rid, body["signer_id"], body["signature_data"])
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "SIGN_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/signature-requests/{rid}/reject",
             dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def reject_request(rid: str, body: dict, db: Session=None):
    for f in ("signer_id", "reason"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    result = ESignatureEngine(db).reject(rid, body["signer_id"], body["reason"])
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "REJECT_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


# ── Approval Templates ─────────────────────────────────────────

@router.get("/companies/{cid}/approval-templates",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_approval_templates(cid: str, user: dict | None=None,
                                  db: Session = Depends(get_db)):
    data = ESignatureEngine(db).list_approval_templates(
        cid, tenant_id=user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/approval-templates",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_approval_template(cid: str, body: dict,
                                   user: dict | None=None,
                                   db: Session = Depends(get_db)):
    for f in ("name", "steps"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    tid = ESignatureEngine(db).create_approval_template(
        user["tenant_id"], cid, body["name"],
        body.get("entity_type"), body["steps"],
        description=body.get("description"))
    db.commit()
    return {"status": "success", "data": {"id": tid}}


@router.get("/approval-templates/{tid}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_approval_template(tid: str, db: Session=None):
    data = ESignatureEngine(db).get_approval_template(tid)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Approval template not found"}})
    return {"status": "success", "data": data}


# ── Delegations ────────────────────────────────────────────────

@router.get("/companies/{cid}/delegations/active",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_active_delegation(cid: str, delegator_id: str | None=None,
                                entity_type: str | None = None,
                                db: Session = Depends(get_db)):
    data = ESignatureEngine(db).get_active_delegation(
        cid, delegator_id, entity_type=entity_type)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "No active delegation found"}})
    return {"status": "success", "data": data}


@router.get("/companies/{cid}/delegations",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_delegations(cid: str, user: dict | None=None,
                           db: Session = Depends(get_db)):
    data = ESignatureEngine(db).list_delegations(
        cid, tenant_id=user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/delegations",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_delegation(cid: str, body: dict,
                            user: dict | None=None,
                            db: Session = Depends(get_db)):
    for f in ("delegator_id", "delegate_id", "start_date", "end_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    did = ESignatureEngine(db).create_delegation(
        user["tenant_id"], cid, body["delegator_id"], body["delegate_id"],
        body["start_date"], body["end_date"],
        entity_type=body.get("entity_type"))
    db.commit()
    return {"status": "success", "data": {"id": did}}
