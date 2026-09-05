"""Advanced tenant-scoped reporting API."""
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from database import SessionLocal
from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from core.reporting_engine import ReportingEngine

router = APIRouter(prefix="/reports", tags=["Advanced Reporting"])

READ_DEPS = [
    Depends(require_permission("reports", "read")),
    Depends(read_limiter.check),
]
WRITE_DEPS = [
    Depends(require_permission("reports", "create")),
    Depends(write_limiter.check),
]


class ReportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    report_type: str = Field(min_length=1, max_length=100)
    format: Literal["json", "csv", "xlsx", "pdf"] = "json"


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        # A reporting request without tenant context must never fall back to global data.
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail={
            "status": "error",
            "error": {"code": "TENANT_CONTEXT_REQUIRED", "message": "Tenant context is required"},
        })
    return str(tenant_id)


@router.get("/profit-and-loss", dependencies=READ_DEPS)
async def profit_and_loss(start_date: Optional[str] = None, end_date: Optional[str] = None,
                          user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).profit_and_loss(_tenant(user), start_date, end_date)}
    finally:
        db.close()


@router.get("/balance-sheet", dependencies=READ_DEPS)
async def balance_sheet(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).balance_sheet(_tenant(user))}
    finally:
        db.close()


@router.get("/cash-flow", dependencies=READ_DEPS)
async def cash_flow(days: int = Query(30, ge=1, le=366), user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).cash_flow(_tenant(user), days)}
    finally:
        db.close()


@router.get("/sales", dependencies=READ_DEPS)
async def sales_report(start_date: Optional[str] = None, end_date: Optional[str] = None,
                       user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).sales_report(_tenant(user), start_date, end_date)}
    finally:
        db.close()


@router.get("/inventory", dependencies=READ_DEPS)
async def inventory_report(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).inventory_report(_tenant(user))}
    finally:
        db.close()


@router.get("/customer-aging", dependencies=READ_DEPS)
async def customer_aging(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).customer_aging(_tenant(user))}
    finally:
        db.close()


@router.get("/industry/{industry}", dependencies=READ_DEPS)
async def industry_report(industry: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).industry_report(_tenant(user), industry)}
    finally:
        db.close()


@router.post("/export", dependencies=WRITE_DEPS)
async def export_report(body: ReportRequest, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return {"status": "success", "data": ReportingEngine(db).export_report(_tenant(user), body.report_type, body.format)}
    finally:
        db.close()
