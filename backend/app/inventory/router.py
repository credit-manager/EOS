from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


# ---------------------------------------------------------------------------
# Warehouses
# ---------------------------------------------------------------------------

@router.post("/warehouses", status_code=201, response_model=schemas.WarehouseResponse)
def create_warehouse(
    payload: schemas.WarehouseCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    warehouse = service.create_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        code=payload.code,
        name=payload.name,
        location=payload.location,
        manager_id=payload.manager_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return warehouse


@router.get("/warehouses", response_model=list[schemas.WarehouseResponse])
def list_warehouses(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_warehouses(db, tenant_id=tenant_id)


@router.get("/warehouses/{warehouse_id}", response_model=schemas.WarehouseResponse)
def get_warehouse(
    warehouse_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)


@router.patch("/warehouses/{warehouse_id}", response_model=schemas.WarehouseResponse)
def update_warehouse(
    warehouse_id: UUID,
    payload: schemas.WarehouseUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    warehouse = service.update_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        warehouse_id=warehouse_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return warehouse


@router.delete("/warehouses/{warehouse_id}", status_code=204)
def delete_warehouse(
    warehouse_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        warehouse_id=warehouse_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Product Categories
# ---------------------------------------------------------------------------

@router.post("/categories", status_code=201, response_model=schemas.ProductCategoryResponse)
def create_category(
    payload: schemas.ProductCategoryCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    category = service.create_category(
        db,
        tenant_id=principal.tenant_id,
        code=payload.code,
        name=payload.name,
        parent_id=payload.parent_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return category


@router.get("/categories", response_model=list[schemas.ProductCategoryResponse])
def list_categories(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_categories(db, tenant_id=tenant_id)


@router.get("/categories/{category_id}", response_model=schemas.ProductCategoryResponse)
def get_category(
    category_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_category(db, tenant_id=tenant_id, category_id=category_id)


@router.patch("/categories/{category_id}", response_model=schemas.ProductCategoryResponse)
def update_category(
    category_id: UUID,
    payload: schemas.ProductCategoryUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    category = service.update_category(
        db,
        tenant_id=principal.tenant_id,
        category_id=category_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_category(
        db,
        tenant_id=principal.tenant_id,
        category_id=category_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@router.post("/products", status_code=201, response_model=schemas.ProductResponse)
def create_product(
    payload: schemas.ProductCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    product = service.create_product(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        unit=payload.unit,
        unit_cost=payload.unit_cost,
        reorder_level=payload.reorder_level,
        is_active=payload.is_active,
        category_id=payload.category_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return product


@router.get("/products", response_model=list[schemas.ProductResponse])
def list_products(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_products(db, tenant_id=tenant_id)


@router.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(
    product_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_product(db, tenant_id=tenant_id, product_id=product_id)


@router.patch("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: UUID,
    payload: schemas.ProductUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    product = service.update_product(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        product_id=product_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_product(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        product_id=product_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Stock Levels
# ---------------------------------------------------------------------------

@router.get("/stock-levels", response_model=list[schemas.StockLevelResponse])
def list_stock_levels(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_stock_levels(db, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Stock Movements
# ---------------------------------------------------------------------------

@router.post("/movements", status_code=201, response_model=schemas.StockMovementResponse)
def create_movement(
    payload: schemas.StockMovementCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    movement = service.record_stock_movement(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference=payload.reference,
        notes=payload.notes,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return movement


@router.get("/movements", response_model=list[schemas.StockMovementResponse])
def list_movements(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_stock_movements(db, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Purchase Requisitions
# ---------------------------------------------------------------------------

@router.post("/requisitions", status_code=201, response_model=schemas.PurchaseRequisitionResponse)
def create_requisition(
    payload: schemas.PurchaseRequisitionCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    req = service.create_requisition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        requisition_number=payload.requisition_number,
        priority=payload.priority,
        lines=[line.model_dump() for line in payload.lines],
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return req


@router.get("/requisitions", response_model=list[schemas.PurchaseRequisitionResponse])
def list_requisitions(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_requisitions(db, tenant_id=tenant_id)


@router.get("/requisitions/{requisition_id}", response_model=schemas.PurchaseRequisitionResponse)
def get_requisition(
    requisition_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_requisition(db, tenant_id=tenant_id, requisition_id=requisition_id)


@router.patch("/requisitions/{requisition_id}", response_model=schemas.PurchaseRequisitionResponse)
def update_requisition(
    requisition_id: UUID,
    payload: schemas.PurchaseRequisitionUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    req = service.update_requisition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        requisition_id=requisition_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return req


@router.delete("/requisitions/{requisition_id}", status_code=204)
def delete_requisition(
    requisition_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_requisition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        requisition_id=requisition_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
