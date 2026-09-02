"""
P21 ERP Foundation Router — Company, Branch, Department, Fiscal Year, Currency, Cost Center
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.erp_foundation import ERPFoundationEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["ERP Foundation"])


def _engine(db: Session=None):
    return ERPFoundationEngine(db)


def _tenant(user: dict):
    return user.get("tenant_id")


# ── COMPANIES ──

@router.get("/companies", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_companies(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_companies(_tenant(user))}


@router.post("/companies", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_company(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "code and name_en required"}})
    eng = ERPFoundationEngine(db)
    cid = eng.create_company(_tenant(user), body["code"], body["name_en"], **{k: v for k, v in body.items() if k not in ("code", "name_en")})
    if not cid:
        raise HTTPException(409, detail={"status": "error", "error": {"code": "DUPLICATE", "message": f"Company code '{body['code']}' already exists"}})
    db.commit()
    return {"status": "success", "data": {"id": cid}}


@router.get("/companies/{company_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_company(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    c = ERPFoundationEngine(db).get_company(company_id, tenant_id=_tenant(user))
    if not c:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Company not found"}})
    return {"status": "success", "data": c}


@router.put("/companies/{company_id}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_company(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    ok = ERPFoundationEngine(db).update_company(company_id, body, _tenant(user))
    if not ok:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "NO_CHANGES", "message": "No valid fields to update"}})
    db.commit()
    return {"status": "success", "message": "Company updated"}


# ── BRANCHES ──

@router.get("/companies/{company_id}/branches", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_branches(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_branches(company_id, _tenant(user))}


@router.post("/companies/{company_id}/branches", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_branch(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "code and name_en required"}})
    bid = ERPFoundationEngine(db).create_branch(_tenant(user), company_id, body["code"], body["name_en"],
                                                 name_ar=body.get("name_ar"), address=body.get("address"),
                                                 city=body.get("city"), country=body.get("country"),
                                                 is_headquarters=body.get("is_headquarters", False))
    db.commit()
    return {"status": "success", "data": {"id": bid}}


# ── DEPARTMENTS ──

@router.get("/companies/{company_id}/departments", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_departments(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_departments(company_id, _tenant(user))}


@router.get("/companies/{company_id}/departments/tree", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_department_tree(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_department_tree(company_id, _tenant(user))}


@router.post("/companies/{company_id}/departments", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_department(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "code and name_en required"}})
    did = ERPFoundationEngine(db).create_department(_tenant(user), company_id, body["code"], body["name_en"],
                                                     parent_id=body.get("parent_id"), branch_id=body.get("branch_id"),
                                                     manager_id=body.get("manager_id"))
    db.commit()
    return {"status": "success", "data": {"id": did}}


# ── FISCAL YEARS ──

@router.get("/companies/{company_id}/fiscal-years", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_fiscal_years(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_fiscal_years(company_id, _tenant(user))}


@router.post("/companies/{company_id}/fiscal-years", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_fiscal_year(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    required = ["code", "name", "start_date", "end_date"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    fyid = ERPFoundationEngine(db).create_fiscal_year(_tenant(user), company_id, body["code"], body["name"],
                                                       body["start_date"], body["end_date"])
    db.commit()
    return {"status": "success", "data": {"id": fyid}}


@router.post("/fiscal-years/{fy_id}/close", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def close_fiscal_year(fy_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    ok = ERPFoundationEngine(db).close_fiscal_year(fy_id, _tenant(user))
    if not ok:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "NOT_CLOSEABLE", "message": "Year not found or already closed"}})
    db.commit()
    return {"status": "success", "message": "Fiscal year closed"}


# ── CURRENCIES ──

@router.get("/currencies", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_currencies(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_currencies(_tenant(user))}


# ── COST CENTERS ──

@router.get("/companies/{company_id}/cost-centers", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_cost_centers(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": ERPFoundationEngine(db).get_cost_centers(company_id, _tenant(user))}


@router.post("/companies/{company_id}/cost-centers", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_cost_center(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "code and name_en required"}})
    ccid = ERPFoundationEngine(db).create_cost_center(_tenant(user), company_id, body["code"], body["name_en"],
                                                       name_ar=body.get("name_ar"), parent_id=body.get("parent_id"),
                                                       budget_amount=body.get("budget_amount", 0))
    db.commit()
    return {"status": "success", "data": {"id": ccid}}
