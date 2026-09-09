from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.identity_engine import IdentityEngine

router = APIRouter(prefix="/api/v1/dynamic/identity", tags=["Identity & SSO"])


@router.get("/providers", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_providers(is_active: bool = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IdentityEngine(db).list_providers(user["tenant_id"], is_active=is_active)}


@router.post("/providers", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_provider(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["provider_name", "provider_type", "client_id"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = IdentityEngine(db).create_provider(user["tenant_id"], body["provider_name"],
        body["provider_type"], body["client_id"], client_secret=body.get("client_secret"),
        metadata_url=body.get("metadata_url"))
    db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Provider created"}}


@router.put("/providers/{provider_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_provider(provider_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IdentityEngine(db).update_provider(user["tenant_id"], provider_id, **body)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/sessions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_sessions(user_id: str = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IdentityEngine(db).list_sessions(user["tenant_id"], user_id=user_id)}


@router.post("/sessions", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_session(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["user_id", "provider_id", "sso_session_id"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    sid = IdentityEngine(db).create_session(user["tenant_id"], body["user_id"],
        body["provider_id"], body["sso_session_id"], ip_address=body.get("ip_address"),
        user_agent=body.get("user_agent"), expires_at=body.get("expires_at"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Session created"}}


@router.get("/mfa", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_mfa(user_id: str = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IdentityEngine(db).list_mfa(user["tenant_id"], user_id=user_id)}


@router.post("/mfa", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def setup_mfa(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "user_id" not in body or "mfa_type" not in body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "user_id and mfa_type required"}})
    result = IdentityEngine(db).setup_mfa(user["tenant_id"], body["user_id"], body["mfa_type"])
    db.commit()
    return {"status": "success", "data": result}


@router.put("/mfa/{mfa_id}/enable", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def enable_mfa(mfa_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IdentityEngine(db).enable_mfa(user["tenant_id"], mfa_id)
    db.commit()
    return {"status": "success", "data": result}


@router.put("/mfa/{mfa_id}/disable", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def disable_mfa(mfa_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IdentityEngine(db).disable_mfa(user["tenant_id"], mfa_id)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/role-mappings", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_role_mappings(provider_id: str = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IdentityEngine(db).list_role_mappings(user["tenant_id"], provider_id=provider_id)}


@router.post("/role-mappings", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_role_mapping(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ["provider_id", "external_role", "internal_role"]:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = IdentityEngine(db).create_role_mapping(user["tenant_id"], body["provider_id"],
        body["external_role"], body["internal_role"])
    db.commit()
    return {"status": "success", "data": {"id": rid, "message": "Role mapping created"}}


@router.delete("/role-mappings/{mapping_id}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_role_mapping(mapping_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IdentityEngine(db).delete_role_mapping(user["tenant_id"], mapping_id)
    if not result:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Not found"}})
    db.commit()
    return {"status": "success", "data": {"deleted": True}}


@router.get("/api-keys", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_api_keys(is_active: bool = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": IdentityEngine(db).list_api_keys(user["tenant_id"], is_active=is_active)}


@router.post("/api-keys", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_api_key(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "key_name" not in body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "key_name required"}})
    result = IdentityEngine(db).create_api_key(user["tenant_id"], body["key_name"],
        permissions=body.get("permissions"), expires_at=body.get("expires_at"))
    db.commit()
    return {"status": "success", "data": result}


@router.put("/api-keys/{key_id}/revoke", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def revoke_api_key(key_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = IdentityEngine(db).revoke_api_key(user["tenant_id"], key_id)
    db.commit()
    return {"status": "success", "data": result}
