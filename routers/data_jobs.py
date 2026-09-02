"""
P18 Data Jobs Router — CRUD + execute + cancel
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.data_jobs import DataJobEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Data Jobs"]
)


@router.get(
    "/jobs",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_jobs(
    job_type: str | None = None,
    status: str | None = None,
    entity_code: str | None = None,
    limit: int | None=None,
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List data jobs."""
    engine = DataJobEngine(db)
    tenant_id = user.get("tenant_id") if user else None

    jobs = engine.list_jobs(
        tenant_id=tenant_id, job_type=job_type,
        status=status, entity_code=entity_code,
        limit=limit, offset=offset,
    )
    return {"status": "success", "data": jobs}


@router.post(
    "/jobs",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def create_job(
    body: dict,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Create a data job."""
    engine = DataJobEngine(db)

    code = body.get("code")
    name_en = body.get("name_en")
    job_type = body.get("job_type")

    if not code or not name_en or not job_type:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "code, name_en, job_type required"},
        })

    if job_type not in DataJobEngine.VALID_JOB_TYPES:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "INVALID_TYPE",
                      "message": f"job_type must be one of: {DataJobEngine.VALID_JOB_TYPES}"},
        })

    tenant_id = user.get("tenant_id")
    user_id = user.get("id") or user.get("user_id")

    job_id = engine.create_job(
        code=code, name_en=name_en, job_type=job_type,
        tenant_id=tenant_id, name_ar=body.get("name_ar"),
        entity_code=body.get("entity_code"),
        config=body.get("config", {}),
        priority=body.get("priority", 0),
        scheduled_at=body.get("scheduled_at"),
        created_by=user_id,
    )
    db.commit()

    return {"status": "success", "data": {"id": job_id, "code": code}}


@router.get(
    "/jobs/{job_id}",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def get_job(
    job_id: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Get a data job."""
    engine = DataJobEngine(db)
    tenant_id = user.get("tenant_id") if user else None

    job = engine.get_job(job_id, tenant_id=tenant_id)
    if not job:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Job not found"},
        })
    return {"status": "success", "data": job}


@router.post(
    "/jobs/{job_id}/execute",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def execute_job(
    job_id: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Execute a data job synchronously."""
    engine = DataJobEngine(db)
    result = engine.execute_job(job_id)

    if not result["success"]:
        status_code = 404 if result.get("error") == "Job not found" else 400
        raise HTTPException(status_code=status_code, detail={
            "status": "error",
            "error": {"code": "EXECUTION_FAILED", "message": result.get("error", "Unknown error")},
        })

    db.commit()
    return {"status": "success", "data": result}


@router.post(
    "/jobs/{job_id}/cancel",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def cancel_job(
    job_id: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Cancel a data job."""
    engine = DataJobEngine(db)
    result = engine.cancel_job(job_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "CANCEL_FAILED", "message": result.get("error", "Cannot cancel")},
        })

    db.commit()
    return {"status": "success", "data": result}
