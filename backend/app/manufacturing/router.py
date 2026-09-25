from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .models import BOM, BOMItem, WorkOrder, ProductionTracking, QualityInspection
from .schemas import (
    BOMCreate, BOMUpdate, BOMResponse,
    BOMItemCreate, BOMItemResponse,
    WorkOrderCreate, WorkOrderResponse,
    ProductionTrackingCreate, ProductionTrackingResponse,
    QualityInspectionCreate, QualityInspectionResponse,
)

router = APIRouter(prefix="/api/v1/manufacturing", tags=["manufacturing"])


# ── BOMs ──

@router.post("/boms", response_model=BOMResponse, status_code=201)
def create_bom(
    payload: BOMCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = BOM(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/boms", response_model=list[BOMResponse])
def list_boms(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(BOM)
        .filter(BOM.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/boms/{bom_id}", response_model=BOMResponse)
def get_bom(
    bom_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(BOM).filter(BOM.id == bom_id, BOM.tenant_id == tenant_id).first()
    if not obj:
        raise HTTPException(404, "BOM not found")
    return obj


@router.patch("/boms/{bom_id}", response_model=BOMResponse)
def update_bom(
    bom_id: int,
    payload: BOMUpdate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(BOM).filter(BOM.id == bom_id, BOM.tenant_id == tenant_id).first()
    if not obj:
        raise HTTPException(404, "BOM not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/boms/{bom_id}", status_code=204, response_model=None)
def delete_bom(
    bom_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(BOM).filter(BOM.id == bom_id, BOM.tenant_id == tenant_id).first()
    if not obj:
        raise HTTPException(404, "BOM not found")
    db.delete(obj)
    db.commit()


@router.post("/boms/{bom_id}/items", response_model=BOMItemResponse, status_code=201)
def add_bom_item(
    bom_id: int,
    payload: BOMItemCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    bom = db.query(BOM).filter(BOM.id == bom_id, BOM.tenant_id == tenant_id).first()
    if not bom:
        raise HTTPException(404, "BOM not found")
    item = BOMItem(bom_id=bom_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/boms/{bom_id}/items", response_model=list[BOMItemResponse])
def list_bom_items(
    bom_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    bom = db.query(BOM).filter(BOM.id == bom_id, BOM.tenant_id == tenant_id).first()
    if not bom:
        raise HTTPException(404, "BOM not found")
    return db.query(BOMItem).filter(BOMItem.bom_id == bom_id).all()


# ── Work Orders ──

@router.post("/work-orders", response_model=WorkOrderResponse, status_code=201)
def create_work_order(
    payload: WorkOrderCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = WorkOrder(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/work-orders", response_model=list[WorkOrderResponse])
def list_work_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(WorkOrder)
        .filter(WorkOrder.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/work-orders/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Work order not found")
    return obj


@router.post("/work-orders/{work_order_id}/start", response_model=WorkOrderResponse)
def start_work_order(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Work order not found")
    if obj.status != "planned":
        raise HTTPException(400, f"Cannot start work order in '{obj.status}' status")
    obj.status = "in_progress"
    obj.actual_start = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/work-orders/{work_order_id}/complete", response_model=WorkOrderResponse)
def complete_work_order(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Work order not found")
    if obj.status != "in_progress":
        raise HTTPException(400, f"Cannot complete work order in '{obj.status}' status")
    obj.status = "completed"
    obj.actual_end = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/work-orders/{work_order_id}/close", response_model=WorkOrderResponse)
def close_work_order(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Work order not found")
    if obj.status != "completed":
        raise HTTPException(400, f"Cannot close work order in '{obj.status}' status")
    obj.status = "closed"
    db.commit()
    db.refresh(obj)
    return obj


# ── Production Tracking ──

@router.post(
    "/work-orders/{work_order_id}/tracking",
    response_model=ProductionTrackingResponse,
    status_code=201,
)
def add_production_tracking(
    work_order_id: int,
    payload: ProductionTrackingCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not wo:
        raise HTTPException(404, "Work order not found")
    entry = ProductionTracking(work_order_id=work_order_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get(
    "/work-orders/{work_order_id}/tracking",
    response_model=list[ProductionTrackingResponse],
)
def list_production_tracking(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not wo:
        raise HTTPException(404, "Work order not found")
    return (
        db.query(ProductionTracking)
        .filter(ProductionTracking.work_order_id == work_order_id)
        .all()
    )


# ── Quality Inspections ──

@router.post(
    "/work-orders/{work_order_id}/inspections",
    response_model=QualityInspectionResponse,
    status_code=201,
)
def add_quality_inspection(
    work_order_id: int,
    payload: QualityInspectionCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not wo:
        raise HTTPException(404, "Work order not found")
    insp = QualityInspection(work_order_id=work_order_id, **payload.model_dump())
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


@router.get(
    "/work-orders/{work_order_id}/inspections",
    response_model=list[QualityInspectionResponse],
)
def list_quality_inspections(
    work_order_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(
        WorkOrder.id == work_order_id, WorkOrder.tenant_id == tenant_id
    ).first()
    if not wo:
        raise HTTPException(404, "Work order not found")
    return (
        db.query(QualityInspection)
        .filter(QualityInspection.work_order_id == work_order_id)
        .all()
    )
