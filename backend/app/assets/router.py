from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


# ---------------------------------------------------------------------------
# Asset Categories
# ---------------------------------------------------------------------------

@router.post("/categories", status_code=201, response_model=schemas.AssetCategoryResponse)
def create_asset_category(
    payload: schemas.AssetCategoryCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    category = service.create_asset_category(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return category


@router.get("/categories", response_model=list[schemas.AssetCategoryResponse])
def list_asset_categories(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_asset_categories(db, tenant_id=tenant_id)


@router.get("/categories/{category_id}", response_model=schemas.AssetCategoryResponse)
def get_asset_category(
    category_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_asset_category(db, tenant_id=tenant_id, category_id=category_id)


@router.patch("/categories/{category_id}", response_model=schemas.AssetCategoryResponse)
def update_asset_category(
    category_id: UUID,
    payload: schemas.AssetCategoryUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    category = service.update_asset_category(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        category_id=category_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_asset_category(
    category_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_asset_category(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        category_id=category_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Maintenance Schedules
# ---------------------------------------------------------------------------

@router.post(
    "/schedules", status_code=201, response_model=schemas.MaintenanceScheduleResponse
)
def create_maintenance_schedule(
    payload: schemas.MaintenanceScheduleCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    schedule = service.create_maintenance_schedule(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        asset_id=payload.asset_id,
        frequency=payload.frequency,
        next_due_date=payload.next_due_date,
        last_performed=payload.last_performed,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return schedule


@router.get("/schedules", response_model=list[schemas.MaintenanceScheduleResponse])
def list_maintenance_schedules(
    asset_id: UUID | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_maintenance_schedules(db, tenant_id=tenant_id, asset_id=asset_id)


@router.get(
    "/schedules/{schedule_id}", response_model=schemas.MaintenanceScheduleResponse
)
def get_maintenance_schedule(
    schedule_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_maintenance_schedule(
        db, tenant_id=tenant_id, schedule_id=schedule_id
    )


@router.patch(
    "/schedules/{schedule_id}", response_model=schemas.MaintenanceScheduleResponse
)
def update_maintenance_schedule(
    schedule_id: UUID,
    payload: schemas.MaintenanceScheduleUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    schedule = service.update_maintenance_schedule(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        schedule_id=schedule_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_maintenance_schedule(
    schedule_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_maintenance_schedule(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        schedule_id=schedule_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Maintenance Logs
# ---------------------------------------------------------------------------

@router.post("/logs", status_code=201, response_model=schemas.MaintenanceLogResponse)
def create_maintenance_log(
    payload: schemas.MaintenanceLogCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    log = service.create_maintenance_log(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        asset_id=payload.asset_id,
        schedule_id=payload.schedule_id,
        maintenance_type=payload.maintenance_type,
        description=payload.description,
        cost=payload.cost,
        performed_by=payload.performed_by,
        performed_at=payload.performed_at,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return log


@router.get("/logs", response_model=list[schemas.MaintenanceLogResponse])
def list_maintenance_logs(
    asset_id: UUID | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_maintenance_logs(db, tenant_id=tenant_id, asset_id=asset_id)


@router.get("/logs/{log_id}", response_model=schemas.MaintenanceLogResponse)
def get_maintenance_log(
    log_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_maintenance_log(db, tenant_id=tenant_id, log_id=log_id)


# ---------------------------------------------------------------------------
# Assets (must be AFTER sub-resource routes to avoid /{asset_id} catching them)
# ---------------------------------------------------------------------------

@router.post("", status_code=201, response_model=schemas.AssetResponse)
def create_asset(
    payload: schemas.AssetCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    asset = service.create_asset(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        asset_code=payload.asset_code,
        name=payload.name,
        category_id=payload.category_id,
        description=payload.description,
        purchase_date=payload.purchase_date,
        purchase_cost=payload.purchase_cost,
        current_value=payload.current_value,
        status=payload.status,
        location=payload.location,
        assigned_to=payload.assigned_to,
        warranty_expiry=payload.warranty_expiry,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return asset


@router.get("", response_model=list[schemas.AssetResponse])
def list_assets(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_assets(db, tenant_id=tenant_id)


@router.get("/{asset_id}", response_model=schemas.AssetResponse)
def get_asset(
    asset_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_asset(db, tenant_id=tenant_id, asset_id=asset_id)


@router.patch("/{asset_id}", response_model=schemas.AssetResponse)
def update_asset(
    asset_id: UUID,
    payload: schemas.AssetUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    asset = service.update_asset(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        asset_id=asset_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_asset(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        asset_id=asset_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
