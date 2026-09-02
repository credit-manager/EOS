from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.system_engine import SystemEngine
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["System Integration"])


# ------------------------------------------------------------------ system config
@router.get("/system/config",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_configs(category: str | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = SystemEngine(db).list_configs(user["tenant_id"], category=category)
    return {"status": "success", "data": data}


@router.post("/system/config",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def set_config(body: dict,
                    user: dict | None=None, db: Session = Depends(get_db)):
    required = ["config_key", "config_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    cid = SystemEngine(db).set_config(
        user["tenant_id"], body["config_key"], body["config_value"],
        description=body.get("description"),
        category=body.get("category", "general"),
        is_sensitive=body.get("is_sensitive", False),
    )
    db.commit()
    return {"status": "success", "data": {"id": cid, "message": "Config saved"}}


@router.delete("/system/config/{key}",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_config(key: str,
                       user: dict | None=None, db: Session = Depends(get_db)):
    result = SystemEngine(db).delete_config(user["tenant_id"], key)
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Config not found"}})
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ system health
@router.get("/system/health",
            dependencies=[Depends(read_limiter.check)])
async def get_health(db: Session=None):
    data = SystemEngine(db).get_system_health()
    return {"status": "success", "data": data}


# -------------------------------------------------------------- integration logs
@router.get("/integration-logs",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_integration_logs(integration_type: str | None = None, status: str | None = None,
                                limit: int = 100,
                                user: dict | None=None, db: Session = Depends(get_db)):
    data = SystemEngine(db).list_integration_logs(
        user["tenant_id"], integration_type=integration_type,
        status=status, limit=limit)
    return {"status": "success", "data": data}


@router.post("/integration-logs",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_integration_log(body: dict,
                                user: dict | None=None, db: Session = Depends(get_db)):
    required = ["integration_type", "direction", "status"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = SystemEngine(db).log_integration(
        user["tenant_id"], body["integration_type"], body["direction"],
        body["status"],
        company_id=body.get("company_id"),
        entity_type=body.get("entity_type"),
        entity_id=body.get("entity_id"),
        payload_summary=body.get("payload_summary"),
        error_message=body.get("error_message"),
        duration_ms=body.get("duration_ms"),
    )
    db.commit()
    return {"status": "success", "data": {"id": lid, "message": "Log created"}}


# ------------------------------------------------------------------ data imports
@router.get("/companies/{cid}/data-imports",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_data_imports(cid: str, status: str | None = None,
                           user: dict | None=None, db: Session = Depends(get_db)):
    data = SystemEngine(db).list_data_imports(cid, tenant_id=user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/data-imports",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_data_import(cid: str, body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    if "import_type" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "import_type required"}})
    iid = SystemEngine(db).create_data_import(
        user["tenant_id"], cid, body["import_type"],
        file_name=body.get("file_name"),
        record_count=body.get("record_count", 0),
        created_by=user.get("sub"),
    )
    db.commit()
    return {"status": "success", "data": {"id": iid, "message": "Import created"}}


@router.put("/data-imports/{iid}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_data_import(iid: str, body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    result = SystemEngine(db).update_data_import(
        iid, tenant_id=user["tenant_id"],
        success_count=body.get("success_count"),
        error_count=body.get("error_count"),
        status=body.get("status"),
        errors=body.get("errors"),
        completed_at=body.get("completed_at"),
    )
    if not result:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Import not found"}})
    return {"status": "success", "data": result}


# ------------------------------------------------------------------ data exports
@router.get("/companies/{cid}/data-exports",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_data_exports(cid: str, export_type: str | None = None,
                           user: dict | None=None, db: Session = Depends(get_db)):
    data = SystemEngine(db).list_data_exports(cid, tenant_id=user["tenant_id"], export_type=export_type)
    return {"status": "success", "data": data}


@router.post("/companies/{cid}/data-exports",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_data_export(cid: str, body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    required = ["export_type", "record_count"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    eid = SystemEngine(db).create_data_export(
        user["tenant_id"], cid, body["export_type"], body["record_count"],
        file_format=body.get("file_format", "csv"),
        download_url=body.get("download_url"),
        created_by=user.get("sub"),
    )
    db.commit()
    return {"status": "success", "data": {"id": eid, "message": "Export created"}}
