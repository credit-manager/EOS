"""Advanced Reporting API Router — authenticated tenant-scoped reports."""
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel
from core.auth_adapter import get_current_user
from core.reporting_engine import ReportingEngine
from database import SessionLocal

router = APIRouter(prefix="/reports", tags=["Advanced Reporting"])

class ReportRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    report_type: str
    format: str | None = "json"

def _db_report(user, fn):
    db=SessionLocal()
    try:return fn(ReportingEngine(db),user["tenant_id"])
    finally:db.close()

@router.get("/profit-and-loss")
async def profit_and_loss(start_date: str|None=None,end_date: str|None=None,user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.profit_and_loss(t,start_date,end_date))}

@router.get("/balance-sheet")
async def balance_sheet(user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.balance_sheet(t))}

@router.get("/cash-flow")
async def cash_flow(days: int=30,user: dict=Depends(get_current_user)):
    if days<1 or days>3660: raise HTTPException(400,"days must be between 1 and 3660")
    return {"status":"success","data":_db_report(user,lambda e,t:e.cash_flow(t,days))}

@router.get("/sales")
async def sales_report(start_date: str|None=None,end_date: str|None=None,user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.sales_report(t,start_date,end_date))}

@router.get("/inventory")
async def inventory_report(user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.inventory_report(t))}

@router.get("/customer-aging")
async def customer_aging(user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.customer_aging(t))}

@router.get("/industry/{industry}")
async def industry_report(industry: str,user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.industry_report(t,industry))}

@router.post("/export")
async def export_report(body: ReportRequest,user: dict=Depends(get_current_user)):
    return {"status":"success","data":_db_report(user,lambda e,t:e.export_report(t,body.report_type,body.format))}
