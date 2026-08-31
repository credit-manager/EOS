"""
P53 AI Composer Router — AI Business Composer
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.ai_composer import AIComposerEngine

router = APIRouter(prefix="/api/v1/dynamic/composer", tags=["AI Composer"])


@router.post("/compose", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def compose(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_input = body.get("input") or body.get("natural_language_input")
    if not user_input:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "input required"}})
    result = AIComposerEngine(db).create_session(
        user.get("tenant_id"), user.get("id") or "unknown", user_input)
    db.commit()
    return {"status": "success", "data": result}


@router.get("/sessions/{session_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_session(session_id: str, db: Session = Depends(get_db)):
    s = AIComposerEngine(db).get_session(session_id)
    if not s:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Session not found"}})
    return {"status": "success", "data": s}


@router.post("/sessions/{session_id}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve(session_id: str, body: dict = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = AIComposerEngine(db).approve_session(session_id, user.get("id") or "admin")
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/sessions/{session_id}/activate", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def activate(session_id: str, db: Session = Depends(get_db)):
    result = AIComposerEngine(db).activate_session(session_id)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "ACTIVATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/sessions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_sessions(status: Optional[str] = None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AIComposerEngine(db).list_sessions(user.get("tenant_id"), status=status)}
