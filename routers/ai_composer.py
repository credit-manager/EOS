"""P53 AI Composer Router — tenant-scoped business configuration sessions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.ai_composer import AIComposerEngine
from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db
from security.tenant_scope import require_tenant_access

router = APIRouter(prefix="/api/v1/dynamic/composer", tags=["AI Composer"])


def _session_tenant(db: Session, session_id: str):
    row = db.execute(text("SELECT tenant_id FROM dbp_ai_composer_sessions WHERE id = :sid"), {"sid": session_id}).fetchone()
    if not row:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Session not found"}})
    return row[0]


def _authorize_session(db: Session, session_id: str, user: dict):
    tenant_id = _session_tenant(db, session_id)
    require_tenant_access(user, tenant_id)
    return tenant_id


@router.post("/compose", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def compose(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    user_input = body.get("input") or body.get("natural_language_input")
    if not user_input:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "input required"}})
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Authenticated user has no tenant")
    result = AIComposerEngine(db).create_session(tenant_id, user.get("id") or "unknown", user_input)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/sessions/{session_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_session(session_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    tenant_id = _authorize_session(db, session_id, user)
    # SECURITY FIX (P0): Pass tenant_id to enforce isolation at engine level
    s = AIComposerEngine(db).get_session(session_id, tenant_id=tenant_id)
    if not s:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Session not found"}})
    return {"status": "success", "data": s}


@router.post("/sessions/{session_id}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve(session_id: str, body: dict | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    tenant_id = _authorize_session(db, session_id, user)
    # SECURITY FIX (P0): Pass tenant_id to enforce isolation at engine level
    result = AIComposerEngine(db).approve_session(session_id, user.get("id") or "admin", tenant_id=tenant_id)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/sessions/{session_id}/activate", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def activate(session_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    tenant_id = _authorize_session(db, session_id, user)
    # SECURITY FIX (P0): Pass tenant_id to enforce isolation at engine level
    result = AIComposerEngine(db).activate_session(session_id, tenant_id=tenant_id)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "ACTIVATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/sessions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_sessions(status: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Authenticated user has no tenant")
    return {"status": "success", "data": AIComposerEngine(db).list_sessions(tenant_id, status=status)}
