from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import Asset, AssetCategory, MaintenanceLog, MaintenanceSchedule

# ---------------------------------------------------------------------------
# AssetCategory
# ---------------------------------------------------------------------------

def create_asset_category(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    description: str | None = None,
    request_id: str | None = None,
) -> AssetCategory:
    existing = db.scalar(
        select(AssetCategory).where(
            AssetCategory.tenant_id == tenant_id, AssetCategory.code == code
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="asset category code already exists")
    category = AssetCategory(
        tenant_id=tenant_id,
        code=code,
        name=name,
        description=description,
    )
    db.add(category)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.category.created",
        resource_type="asset_category",
        resource_id=category.id,
        request_id=request_id,
        metadata={"code": code, "name": name},
    )
    db.flush()
    return category


def get_asset_category(db: Session, *, tenant_id: UUID, category_id: UUID) -> AssetCategory:
    category = db.get(AssetCategory, category_id)
    if category is None or category.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="asset category not found")
    return category


def list_asset_categories(db: Session, *, tenant_id: UUID) -> list[AssetCategory]:
    return db.scalars(
        select(AssetCategory)
        .where(AssetCategory.tenant_id == tenant_id)
        .order_by(AssetCategory.created_at.desc())
    ).all()


def update_asset_category(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    category_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> AssetCategory:
    category = get_asset_category(db, tenant_id=tenant_id, category_id=category_id)
    for key, value in data.items():
        if value is not None:
            setattr(category, key, value)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.category.updated",
        resource_type="asset_category",
        resource_id=category.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return category


def delete_asset_category(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    category_id: UUID,
    request_id: str | None = None,
) -> None:
    category = get_asset_category(db, tenant_id=tenant_id, category_id=category_id)
    assets = db.scalars(
        select(Asset).where(Asset.tenant_id == tenant_id, Asset.category_id == category_id)
    ).all()
    if assets:
        raise HTTPException(
            status_code=409, detail="cannot delete category with existing assets"
        )
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.category.deleted",
        resource_type="asset_category",
        resource_id=category.id,
        request_id=request_id,
    )
    db.delete(category)
    db.flush()


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------

def create_asset(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    asset_code: str,
    name: str,
    category_id: UUID | None = None,
    description: str | None = None,
    purchase_date=None,
    purchase_cost: Decimal = Decimal("0"),
    current_value: Decimal = Decimal("0"),
    status: str = "active",
    location: str | None = None,
    assigned_to: UUID | None = None,
    warranty_expiry=None,
    request_id: str | None = None,
) -> Asset:
    if category_id is not None:
        get_asset_category(db, tenant_id=tenant_id, category_id=category_id)
    existing = db.scalar(
        select(Asset).where(Asset.tenant_id == tenant_id, Asset.asset_code == asset_code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="asset code already exists")
    asset = Asset(
        tenant_id=tenant_id,
        created_by=user_id,
        asset_code=asset_code,
        name=name,
        category_id=category_id,
        description=description,
        purchase_date=purchase_date,
        purchase_cost=purchase_cost,
        current_value=current_value,
        status=status,
        location=location,
        assigned_to=assigned_to,
        warranty_expiry=warranty_expiry,
    )
    db.add(asset)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.asset.created",
        resource_type="asset",
        resource_id=asset.id,
        request_id=request_id,
        metadata={"asset_code": asset_code, "name": name},
    )
    db.flush()
    return asset


def get_asset(db: Session, *, tenant_id: UUID, asset_id: UUID) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None or asset.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset


def list_assets(db: Session, *, tenant_id: UUID) -> list[Asset]:
    return db.scalars(
        select(Asset).where(Asset.tenant_id == tenant_id).order_by(Asset.created_at.desc())
    ).all()


def update_asset(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    asset_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Asset:
    asset = get_asset(db, tenant_id=tenant_id, asset_id=asset_id)
    if "status" in data and data["status"] is not None:
        allowed = _valid_transitions(asset.status)
        if data["status"] not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"cannot transition from '{asset.status}' to '{data['status']}'",
            )
    for key, value in data.items():
        if value is not None:
            setattr(asset, key, value)
    asset.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.asset.updated",
        resource_type="asset",
        resource_id=asset.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return asset


def delete_asset(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    asset_id: UUID,
    request_id: str | None = None,
) -> None:
    asset = get_asset(db, tenant_id=tenant_id, asset_id=asset_id)
    schedules = db.scalars(
        select(MaintenanceSchedule).where(
            MaintenanceSchedule.tenant_id == tenant_id,
            MaintenanceSchedule.asset_id == asset_id,
        )
    ).all()
    if schedules:
        raise HTTPException(
            status_code=409, detail="cannot delete asset with existing maintenance schedules"
        )
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.asset.deleted",
        resource_type="asset",
        resource_id=asset.id,
        request_id=request_id,
    )
    db.delete(asset)
    db.flush()


def _valid_transitions(current: str) -> set[str]:
    transitions: dict[str, set[str]] = {
        "active": {"maintenance", "retired", "disposed"},
        "maintenance": {"active", "retired", "disposed"},
        "retired": {"disposed"},
        "disposed": set(),
    }
    return transitions.get(current, set())


# ---------------------------------------------------------------------------
# MaintenanceSchedule
# ---------------------------------------------------------------------------

def create_maintenance_schedule(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    asset_id: UUID,
    frequency: str,
    next_due_date,
    last_performed=None,
    request_id: str | None = None,
) -> MaintenanceSchedule:
    get_asset(db, tenant_id=tenant_id, asset_id=asset_id)
    schedule = MaintenanceSchedule(
        tenant_id=tenant_id,
        asset_id=asset_id,
        frequency=frequency,
        next_due_date=next_due_date,
        last_performed=last_performed,
    )
    db.add(schedule)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.schedule.created",
        resource_type="maintenance_schedule",
        resource_id=schedule.id,
        request_id=request_id,
        metadata={"asset_id": str(asset_id), "frequency": frequency},
    )
    db.flush()
    return schedule


def get_maintenance_schedule(
    db: Session, *, tenant_id: UUID, schedule_id: UUID
) -> MaintenanceSchedule:
    schedule = db.get(MaintenanceSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="maintenance schedule not found")
    return schedule


def list_maintenance_schedules(
    db: Session, *, tenant_id: UUID, asset_id: UUID | None = None
) -> list[MaintenanceSchedule]:
    stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.tenant_id == tenant_id)
    if asset_id is not None:
        stmt = stmt.where(MaintenanceSchedule.asset_id == asset_id)
    return db.scalars(stmt.order_by(MaintenanceSchedule.next_due_date)).all()


def update_maintenance_schedule(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    schedule_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> MaintenanceSchedule:
    schedule = get_maintenance_schedule(db, tenant_id=tenant_id, schedule_id=schedule_id)
    for key, value in data.items():
        if value is not None:
            setattr(schedule, key, value)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.schedule.updated",
        resource_type="maintenance_schedule",
        resource_id=schedule.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return schedule


def delete_maintenance_schedule(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    schedule_id: UUID,
    request_id: str | None = None,
) -> None:
    schedule = get_maintenance_schedule(db, tenant_id=tenant_id, schedule_id=schedule_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.schedule.deleted",
        resource_type="maintenance_schedule",
        resource_id=schedule.id,
        request_id=request_id,
    )
    db.delete(schedule)
    db.flush()


# ---------------------------------------------------------------------------
# MaintenanceLog
# ---------------------------------------------------------------------------

def create_maintenance_log(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    asset_id: UUID,
    schedule_id: UUID | None = None,
    maintenance_type: str,
    description: str | None = None,
    cost: Decimal = Decimal("0"),
    performed_by: UUID | None = None,
    performed_at: datetime | None = None,
    request_id: str | None = None,
) -> MaintenanceLog:
    get_asset(db, tenant_id=tenant_id, asset_id=asset_id)
    if schedule_id is not None:
        get_maintenance_schedule(db, tenant_id=tenant_id, schedule_id=schedule_id)
    if performed_at is None:
        performed_at = datetime.now(UTC)
    log = MaintenanceLog(
        tenant_id=tenant_id,
        asset_id=asset_id,
        schedule_id=schedule_id,
        maintenance_type=maintenance_type,
        description=description,
        cost=cost,
        performed_by=performed_by,
        performed_at=performed_at,
    )
    db.add(log)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="assets.maintenance_log.created",
        resource_type="maintenance_log",
        resource_id=log.id,
        request_id=request_id,
        metadata={"asset_id": str(asset_id), "maintenance_type": maintenance_type},
    )
    db.flush()
    return log


def get_maintenance_log(
    db: Session, *, tenant_id: UUID, log_id: UUID
) -> MaintenanceLog:
    log = db.get(MaintenanceLog, log_id)
    if log is None or log.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="maintenance log not found")
    return log


def list_maintenance_logs(
    db: Session, *, tenant_id: UUID, asset_id: UUID | None = None
) -> list[MaintenanceLog]:
    stmt = select(MaintenanceLog).where(MaintenanceLog.tenant_id == tenant_id)
    if asset_id is not None:
        stmt = stmt.where(MaintenanceLog.asset_id == asset_id)
    return db.scalars(stmt.order_by(MaintenanceLog.performed_at.desc())).all()
