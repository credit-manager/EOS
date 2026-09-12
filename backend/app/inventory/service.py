from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import (
    Product,
    ProductCategory,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    StockLevel,
    StockMovement,
    Warehouse,
)

_ZERO = Decimal("0")

_VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted"},
    "submitted": {"approved"},
    "approved": {"ordered"},
    "ordered": {"received"},
}


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------

def create_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    location: str | None = None,
    manager_id: UUID | None = None,
    request_id: str | None = None,
) -> Warehouse:
    existing = db.scalar(
        select(Warehouse).where(Warehouse.tenant_id == tenant_id, Warehouse.code == code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="warehouse code already exists")
    warehouse = Warehouse(
        tenant_id=tenant_id,
        created_by=user_id,
        code=code,
        name=name,
        location=location,
        manager_id=manager_id,
    )
    db.add(warehouse)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.warehouse.created",
        resource_type="warehouse",
        resource_id=warehouse.id,
        request_id=request_id,
        metadata={"code": code, "name": name},
    )
    db.flush()
    return warehouse


def get_warehouse(db: Session, *, tenant_id: UUID, warehouse_id: UUID) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="warehouse not found")
    return warehouse


def list_warehouses(db: Session, *, tenant_id: UUID) -> list[Warehouse]:
    return db.scalars(
        select(Warehouse).where(Warehouse.tenant_id == tenant_id).order_by(Warehouse.created_at.desc())
    ).all()


def update_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    warehouse_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Warehouse:
    warehouse = get_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    for key, value in data.items():
        if value is not None:
            setattr(warehouse, key, value)
    warehouse.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.warehouse.updated",
        resource_type="warehouse",
        resource_id=warehouse.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return warehouse


def delete_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    warehouse_id: UUID,
    request_id: str | None = None,
) -> None:
    warehouse = get_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    levels = db.scalars(
        select(StockLevel).where(
            StockLevel.tenant_id == tenant_id, StockLevel.warehouse_id == warehouse_id
        )
    ).all()
    if levels:
        raise HTTPException(status_code=409, detail="cannot delete warehouse with existing stock levels")
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.warehouse.deleted",
        resource_type="warehouse",
        resource_id=warehouse.id,
        request_id=request_id,
    )
    db.delete(warehouse)
    db.flush()


# ---------------------------------------------------------------------------
# Product Category
# ---------------------------------------------------------------------------

def create_category(
    db: Session,
    *,
    tenant_id: UUID,
    code: str,
    name: str,
    parent_id: UUID | None = None,
    request_id: str | None = None,
) -> ProductCategory:
    existing = db.scalar(
        select(ProductCategory).where(
            ProductCategory.tenant_id == tenant_id, ProductCategory.code == code
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="category code already exists")
    category = ProductCategory(
        tenant_id=tenant_id,
        code=code,
        name=name,
        parent_id=parent_id,
    )
    db.add(category)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        action="inventory.category.created",
        resource_type="category",
        resource_id=category.id,
        request_id=request_id,
        metadata={"code": code, "name": name},
    )
    db.flush()
    return category


def get_category(db: Session, *, tenant_id: UUID, category_id: UUID) -> ProductCategory:
    category = db.get(ProductCategory, category_id)
    if category is None or category.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="category not found")
    return category


def list_categories(db: Session, *, tenant_id: UUID) -> list[ProductCategory]:
    return db.scalars(
        select(ProductCategory).where(ProductCategory.tenant_id == tenant_id)
    ).all()


def update_category(
    db: Session,
    *,
    tenant_id: UUID,
    category_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> ProductCategory:
    category = get_category(db, tenant_id=tenant_id, category_id=category_id)
    for key, value in data.items():
        if value is not None:
            setattr(category, key, value)
    audit_record(
        db,
        tenant_id=tenant_id,
        action="inventory.category.updated",
        resource_type="category",
        resource_id=category.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return category


def delete_category(
    db: Session,
    *,
    tenant_id: UUID,
    category_id: UUID,
    request_id: str | None = None,
) -> None:
    category = get_category(db, tenant_id=tenant_id, category_id=category_id)
    children = db.scalars(
        select(ProductCategory).where(ProductCategory.parent_id == category_id)
    ).all()
    if children:
        raise HTTPException(status_code=409, detail="cannot delete category with children")
    products = db.scalars(
        select(Product).where(Product.category_id == category_id)
    ).all()
    if products:
        raise HTTPException(status_code=409, detail="cannot delete category with products")
    audit_record(
        db,
        tenant_id=tenant_id,
        action="inventory.category.deleted",
        resource_type="category",
        resource_id=category.id,
        request_id=request_id,
    )
    db.delete(category)
    db.flush()


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

def create_product(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    sku: str,
    name: str,
    description: str | None = None,
    unit: str,
    unit_cost: Decimal = Decimal("0"),
    reorder_level: int = 0,
    is_active: bool = True,
    category_id: UUID | None = None,
    request_id: str | None = None,
) -> Product:
    existing = db.scalar(
        select(Product).where(Product.tenant_id == tenant_id, Product.sku == sku)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="product SKU already exists")
    if category_id is not None:
        get_category(db, tenant_id=tenant_id, category_id=category_id)
    product = Product(
        tenant_id=tenant_id,
        created_by=user_id,
        sku=sku,
        name=name,
        description=description,
        unit=unit,
        unit_cost=unit_cost,
        reorder_level=reorder_level,
        is_active=is_active,
        category_id=category_id,
    )
    db.add(product)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.product.created",
        resource_type="product",
        resource_id=product.id,
        request_id=request_id,
        metadata={"sku": sku, "name": name},
    )
    db.flush()
    return product


def get_product(db: Session, *, tenant_id: UUID, product_id: UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="product not found")
    return product


def list_products(db: Session, *, tenant_id: UUID) -> list[Product]:
    return db.scalars(
        select(Product).where(Product.tenant_id == tenant_id).order_by(Product.created_at.desc())
    ).all()


def update_product(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Product:
    product = get_product(db, tenant_id=tenant_id, product_id=product_id)
    for key, value in data.items():
        if value is not None:
            setattr(product, key, value)
    product.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.product.updated",
        resource_type="product",
        resource_id=product.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return product


def delete_product(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    request_id: str | None = None,
) -> None:
    product = get_product(db, tenant_id=tenant_id, product_id=product_id)
    levels = db.scalars(
        select(StockLevel).where(StockLevel.product_id == product_id)
    ).all()
    if levels:
        raise HTTPException(status_code=409, detail="cannot delete product with existing stock levels")
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.product.deleted",
        resource_type="product",
        resource_id=product.id,
        request_id=request_id,
    )
    db.delete(product)
    db.flush()


# ---------------------------------------------------------------------------
# Stock Level
# ---------------------------------------------------------------------------

def get_stock_level(
    db: Session, *, tenant_id: UUID, warehouse_id: UUID, product_id: UUID
) -> StockLevel:
    level = db.scalar(
        select(StockLevel).where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.product_id == product_id,
        )
    )
    if level is None:
        raise HTTPException(status_code=404, detail="stock level not found")
    return level


def get_or_create_stock_level(
    db: Session, *, tenant_id: UUID, warehouse_id: UUID, product_id: UUID
) -> StockLevel:
    level = db.scalar(
        select(StockLevel).where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.product_id == product_id,
        )
    )
    if level is None:
        level = StockLevel(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=_ZERO,
            reserved=_ZERO,
        )
        db.add(level)
        db.flush()
    return level


def list_stock_levels(db: Session, *, tenant_id: UUID) -> list[StockLevel]:
    return db.scalars(
        select(StockLevel).where(StockLevel.tenant_id == tenant_id)
    ).all()


# ---------------------------------------------------------------------------
# Stock Movement
# ---------------------------------------------------------------------------

def record_stock_movement(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    warehouse_id: UUID,
    product_id: UUID,
    movement_type: str,
    quantity: Decimal,
    reference: str | None = None,
    notes: str | None = None,
    request_id: str | None = None,
) -> StockMovement:
    get_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    get_product(db, tenant_id=tenant_id, product_id=product_id)
    level = get_or_create_stock_level(
        db, tenant_id=tenant_id, warehouse_id=warehouse_id, product_id=product_id
    )
    if movement_type == "inbound":
        level.quantity += quantity
    elif movement_type == "outbound":
        if level.quantity < quantity:
            raise HTTPException(status_code=409, detail="insufficient stock")
        level.quantity -= quantity
    elif movement_type == "adjustment":
        level.quantity += quantity
    # transfer does not change stock at source (handled by caller)
    level.updated_at = datetime.now(UTC)

    movement = StockMovement(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity=quantity,
        reference=reference,
        notes=notes,
        created_by=user_id,
    )
    db.add(movement)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.movement.recorded",
        resource_type="stock_movement",
        resource_id=movement.id,
        request_id=request_id,
        metadata={
            "movement_type": movement_type,
            "warehouse_id": str(warehouse_id),
            "product_id": str(product_id),
            "quantity": str(quantity),
        },
    )
    db.flush()
    return movement


def list_stock_movements(db: Session, *, tenant_id: UUID) -> list[StockMovement]:
    return db.scalars(
        select(StockMovement).where(StockMovement.tenant_id == tenant_id).order_by(StockMovement.created_at.desc())
    ).all()


# ---------------------------------------------------------------------------
# Purchase Requisition
# ---------------------------------------------------------------------------

def create_requisition(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    requisition_number: str,
    priority: str = "medium",
    lines: list[dict] | None = None,
    request_id: str | None = None,
) -> PurchaseRequisition:
    existing = db.scalar(
        select(PurchaseRequisition).where(
            PurchaseRequisition.tenant_id == tenant_id,
            PurchaseRequisition.requisition_number == requisition_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="requisition number already exists")
    req = PurchaseRequisition(
        tenant_id=tenant_id,
        requisition_number=requisition_number,
        status="draft",
        priority=priority,
        requested_by=user_id,
    )
    db.add(req)
    db.flush()
    for line in (lines or []):
        get_product(db, tenant_id=tenant_id, product_id=line["product_id"])
        req_line = PurchaseRequisitionLine(
            tenant_id=tenant_id,
            requisition_id=req.id,
            product_id=line["product_id"],
            quantity=line["quantity"],
            unit_cost=line.get("unit_cost", _ZERO),
        )
        db.add(req_line)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.requisition.created",
        resource_type="requisition",
        resource_id=req.id,
        request_id=request_id,
        metadata={"requisition_number": requisition_number, "priority": priority},
    )
    db.flush()
    return req


def get_requisition(db: Session, *, tenant_id: UUID, requisition_id: UUID) -> PurchaseRequisition:
    req = db.get(PurchaseRequisition, requisition_id)
    if req is None or req.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="requisition not found")
    return req


def list_requisitions(db: Session, *, tenant_id: UUID) -> list[PurchaseRequisition]:
    return db.scalars(
        select(PurchaseRequisition).where(
            PurchaseRequisition.tenant_id == tenant_id
        ).order_by(PurchaseRequisition.created_at.desc())
    ).all()


def update_requisition(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    requisition_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> PurchaseRequisition:
    req = get_requisition(db, tenant_id=tenant_id, requisition_id=requisition_id)
    new_status = data.get("status")
    if new_status is not None and new_status != req.status:
        allowed = _VALID_STATUS_TRANSITIONS.get(req.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"cannot transition from '{req.status}' to '{new_status}'",
            )
    for key, value in data.items():
        if value is not None:
            setattr(req, key, value)
    req.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.requisition.updated",
        resource_type="requisition",
        resource_id=req.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return req


def delete_requisition(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    requisition_id: UUID,
    request_id: str | None = None,
) -> None:
    req = get_requisition(db, tenant_id=tenant_id, requisition_id=requisition_id)
    if req.status != "draft":
        raise HTTPException(status_code=409, detail="cannot delete non-draft requisition")
    lines = db.scalars(
        select(PurchaseRequisitionLine).where(
            PurchaseRequisitionLine.requisition_id == requisition_id
        )
    ).all()
    for line in lines:
        db.delete(line)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="inventory.requisition.deleted",
        resource_type="requisition",
        resource_id=req.id,
        request_id=request_id,
    )
    db.delete(req)
    db.flush()
