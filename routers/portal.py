"""
P57 Customer Portal Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.customer_portal import CustomerPortalEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


router = APIRouter(prefix="/api/v1/dynamic/portal", tags=["Customer Portal"])


@router.get("/overview", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def overview(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": CustomerPortalEngine(db).get_overview(user.get("tenant_id"))}


@router.post("/support/tickets", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_ticket(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = CustomerPortalEngine(db).create_ticket(
        user.get("tenant_id"), body.get("subject"), body.get("message"),
        body.get("priority", "normal"), user.get("id") or "user")
    if not result["success"]:
        raise _err(400, "TICKET_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": result}


@router.get("/support/tickets", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_tickets(status: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": CustomerPortalEngine(db).list_tickets(
        user.get("tenant_id"), status=status)}


@router.put("/support/tickets/{ticket_id}/close", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def close_ticket(ticket_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    result = CustomerPortalEngine(db).close_ticket(user.get("tenant_id"), ticket_id)
    if not result["success"]:
        raise _err(400, "CLOSE_FAILED", result["error"])
    db.commit()
    return {"status": "success"}
