"""P18 Data Jobs Router — tenant-scoped CRUD + execution + cancellation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.data_jobs import DataJobEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Data Jobs"])


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(401, detail={"status":"error","error":{"code":"TENANT_REQUIRED","message":"Authenticated tenant is required"}})
    return tenant_id


@router.get("/jobs", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_jobs(job_type: str | None = None, status: str | None = None, entity_code: str | None = None,
                    limit: int | None = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                    user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = DataJobEngine(db).list_jobs(tenant_id=_tenant(user), job_type=job_type, status=status,
                                       entity_code=entity_code, limit=limit or 50, offset=offset)
    return {"status":"success","data":jobs}


@router.post("/jobs", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_job(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = _tenant(user)
    code, name_en, job_type = body.get("code"), body.get("name_en"), body.get("job_type")
    if not code or not name_en or not job_type:
        raise HTTPException(400, detail={"status":"error","error":{"code":"MISSING","message":"code, name_en, job_type required"}})
    if job_type not in DataJobEngine.VALID_JOB_TYPES:
        raise HTTPException(400, detail={"status":"error","error":{"code":"INVALID_TYPE","message":"Unsupported job type"}})
    engine=DataJobEngine(db)
    job_id=engine.create_job(code=code,name_en=name_en,job_type=job_type,tenant_id=tenant_id,name_ar=body.get("name_ar"),
                             entity_code=body.get("entity_code"),config=body.get("config",{}),priority=body.get("priority",0),
                             scheduled_at=body.get("scheduled_at"),created_by=user.get("id") or user.get("user_id"))
    if not job_id:
        raise HTTPException(400, detail={"status":"error","error":{"code":"CREATE_FAILED","message":"Unable to create job"}})
    db.commit()
    return {"status":"success","data":{"id":job_id,"code":code}}


@router.get("/jobs/{job_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_job(job_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    job=DataJobEngine(db).get_job(job_id,tenant_id=_tenant(user))
    if not job:
        raise HTTPException(404, detail={"status":"error","error":{"code":"NOT_FOUND","message":"Job not found"}})
    return {"status":"success","data":job}


@router.post("/jobs/{job_id}/execute", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def execute_job(job_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result=DataJobEngine(db).execute_job(job_id,tenant_id=_tenant(user))
    if not result.get("success"):
        code="NOT_FOUND" if result.get("error")=="Job not found" else "EXECUTION_FAILED"
        raise HTTPException(404 if code=="NOT_FOUND" else 400, detail={"status":"error","error":{"code":code,"message":result.get("error","Unknown error")}})
    db.commit()
    return {"status":"success","data":result}


@router.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def cancel_job(job_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result=DataJobEngine(db).cancel_job(job_id,tenant_id=_tenant(user))
    if not result.get("success"):
        code="NOT_FOUND" if result.get("error")=="Job not found" else "CANCEL_FAILED"
        raise HTTPException(404 if code=="NOT_FOUND" else 400, detail={"status":"error","error":{"code":code,"message":result.get("error","Cannot cancel")}})
    db.commit()
    return {"status":"success","data":result}
