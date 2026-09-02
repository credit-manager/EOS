"""
Advanced Reporting API Router
"""

from fastapi import APIRouter
from pydantic import BaseModel

from core.reporting_engine import ReportingEngine
from database import SessionLocal

router = APIRouter(prefix="/reports", tags=["Advanced Reporting"])


class ReportRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    report_type: str
    format: str | None = "json"


@router.get("/profit-and-loss")
async def profit_and_loss(start_date: str | None = None, end_date: str | None = None,
                          user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).profit_and_loss(user["tenant_id"], start_date, end_date)
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/balance-sheet")
async def balance_sheet(user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).balance_sheet(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/cash-flow")
async def cash_flow(days: int = 30, user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).cash_flow(user["tenant_id"], days)
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/sales")
async def sales_report(start_date: str | None = None, end_date: str | None = None,
                       user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).sales_report(user["tenant_id"], start_date, end_date)
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/inventory")
async def inventory_report(user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).inventory_report(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/customer-aging")
async def customer_aging(user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).customer_aging(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/industry/{industry}")
async def industry_report(industry: str, user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).industry_report(user["tenant_id"], industry)
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/export")
async def export_report(body: ReportRequest, user: dict | None=None):
    db = SessionLocal()
    try:
        data = ReportingEngine(db).export_report(user["tenant_id"], body.report_type, body.format)
        return {"status": "success", "data": data}
    finally:
        db.close()
