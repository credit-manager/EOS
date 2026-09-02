"""P54 Self-Service ERP Builder Router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.builder_engine import BuilderEngine
from core.builder_safety import _atomic_ensure_physical_table
from core.rate_limit import read_limiter, write_limiter
from database import get_db

# Install the atomic DDL implementation before any BuilderEngine is used.
BuilderEngine._ensure_physical_table = _atomic_ensure_physical_table


def _err(status_code, code, message):
    return HTTPException(status_code, detail={"status": "error", "error": {"code": code, "message": message}})

router = APIRouter(prefix="/api/v1/dynamic/builder", tags=["ERP Builder"])


@router.post("/projects", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_project(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    name = body.get("name")
    if not name: raise _err(400, "MISSING", "name required")
    result = BuilderEngine(db).create_project(user.get("tenant_id"), name, composer_session_id=body.get("composer_session_id"), initial_config=body.get("initial_config"))
    if not result["success"]: raise _err(400, "CREATE_FAILED", result["error"])
    db.commit(); return {"status": "success", "data": result}

@router.get("/projects", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_projects(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BuilderEngine(db).list_projects(user.get("tenant_id"))}

@router.get("/projects/{pid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_project(pid: str, user: dict | None=None, db: Session = Depends(get_db)):
    proj = BuilderEngine(db).get_project(user.get("tenant_id"), pid)
    if not proj: raise _err(404, "NOT_FOUND", "Project not found")
    return {"status": "success", "data": proj}

@router.put("/projects/{pid}/settings", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_settings(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not BuilderEngine(db).update_settings(user.get("tenant_id"), pid, body): raise _err(404, "NOT_FOUND", "Project not found")
    db.commit(); return {"status": "success"}

@router.put("/projects/{pid}/modules", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def set_modules(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    modules = body.get("modules")
    if not isinstance(modules, list): raise _err(400, "MISSING", "modules list required")
    result = BuilderEngine(db).set_modules(user.get("tenant_id"), pid, modules)
    if not result["success"]: raise _err(400, "MODULES_FAILED", result["error"])
    db.commit(); return {"status": "success"}

@router.post("/projects/{pid}/entities", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_entity(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).add_entity(user.get("tenant_id"), pid, body)
    if not result["success"]: raise _err(400, "ENTITY_FAILED", result["error"])
    db.commit(); return {"status": "success", "data": result}

@router.delete("/projects/{pid}/entities/{ecode}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def remove_entity(pid: str, ecode: str, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).remove_entity(user.get("tenant_id"), pid, ecode)
    if not result["success"]: raise _err(400, "ENTITY_FAILED", result["error"])
    db.commit(); return {"status": "success"}

@router.post("/projects/{pid}/relationships", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_relationship(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).add_relationship(user.get("tenant_id"), pid, body)
    if not result["success"]: raise _err(400, "REL_FAILED", result["error"])
    db.commit(); return {"status": "success"}

@router.put("/projects/{pid}/roles", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def set_roles(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not BuilderEngine(db).set_roles(user.get("tenant_id"), pid, body): raise _err(404, "NOT_FOUND", "Project not found")
    db.commit(); return {"status": "success"}

@router.post("/projects/{pid}/workflows", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_workflow(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).add_workflow(user.get("tenant_id"), pid, body)
    if not result["success"]: raise _err(400, "WF_FAILED", result["error"])
    db.commit(); return {"status": "success"}

@router.post("/projects/{pid}/kpis", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_kpi(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).add_kpi(user.get("tenant_id"), pid, body)
    if not result["success"]: raise _err(400, "KPI_FAILED", result["error"])
    db.commit(); return {"status": "success"}

@router.get("/projects/{pid}/preview", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def preview(pid: str, user: dict | None=None, db: Session = Depends(get_db)):
    data = BuilderEngine(db).preview(user.get("tenant_id"), pid)
    if not data: raise _err(404, "NOT_FOUND", "Project not found")
    return {"status": "success", "data": data}

@router.post("/projects/{pid}/publish", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def publish(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BuilderEngine(db).publish(user.get("tenant_id"), pid, published_by=user.get("id") or "admin", confirmed=bool(body.get("confirmed")), change_summary=body.get("change_summary", ""))
    if not result["success"]:
        code = "VALIDATION_FAILED" if result.get("validation") else "PUBLISH_FAILED"
        raise HTTPException(400, detail={"status": "error", "error": {"code": code, "message": result["error"], "details": result.get("validation")}})
    return {"status": "success", "data": result}

@router.get("/active", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_active(user: dict | None=None, db: Session = Depends(get_db)):
    active = BuilderEngine(db).get_active_config(user.get("tenant_id"))
    if not active: raise _err(404, "NOT_FOUND", "No published configuration for this tenant")
    return {"status": "success", "data": active}

@router.get("/projects/{pid}/versions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_versions(pid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BuilderEngine(db).list_versions(user.get("tenant_id"), pid)}

@router.post("/projects/{pid}/rollback", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def rollback(pid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    version_id = body.get("version_id")
    if not version_id: raise _err(400, "MISSING", "version_id required")
    result = BuilderEngine(db).rollback(user.get("tenant_id"), pid, version_id, rolled_back_by=user.get("id") or "admin")
    if not result["success"]: raise _err(400, "ROLLBACK_FAILED", result["error"])
    return {"status": "success", "data": result}
