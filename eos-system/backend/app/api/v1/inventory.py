"""
EOS System — Inventory Module Router (with RBAC + Audit)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.inventory import Product, Category, Warehouse, StockMovement

router = APIRouter()


# Schemas
class ProductCreate(BaseModel):
    sku: str
    name: str
    name_ar: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_price: Decimal
    cost_price: Decimal
    currency: str = "EGP"
    min_stock: int = 0
    max_stock: Optional[int] = None
    barcode: Optional[str] = None
    is_active: bool = True


class ProductResponse(BaseModel):
    id: str
    sku: str
    name: str
    name_ar: str
    description: Optional[str]
    category_id: Optional[str]
    unit_price: float
    cost_price: float
    currency: str
    current_stock: int
    min_stock: int
    max_stock: Optional[int]
    barcode: Optional[str]
    is_active: bool
    created_at: datetime


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int


class CategoryCreate(BaseModel):
    name: str
    name_ar: str
    parent_id: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    name_ar: str
    parent_id: Optional[str]
    created_at: datetime


class WarehouseCreate(BaseModel):
    name: str
    name_ar: str
    code: str
    address: Optional[str] = None
    manager_id: Optional[str] = None


class WarehouseResponse(BaseModel):
    id: str
    name: str
    name_ar: str
    code: str
    address: Optional[str]
    is_active: bool
    created_at: datetime


class StockMovementCreate(BaseModel):
    product_id: str
    warehouse_id: str
    movement_type: str  # inbound, outbound, transfer, adjustment
    quantity: int
    reference: Optional[str] = None
    notes: Optional[str] = None
    movement_date: date


class StockMovementResponse(BaseModel):
    id: str
    product_id: str
    warehouse_id: str
    movement_type: str
    quantity: int
    reference: Optional[str]
    notes: Optional[str]
    movement_date: date
    created_at: datetime


class StockMovementListResponse(BaseModel):
    movements: List[StockMovementResponse]
    total: int


class LowStockAlert(BaseModel):
    product_id: str
    sku: str
    name: str
    name_ar: str
    current_stock: int
    min_stock: int
    warehouse_name: Optional[str]


# ─── PRODUCTS ─────────────────────────────────────────────

@router.get("/products", response_model=ProductListResponse)
async def list_products(
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    low_stock: Optional[bool] = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    query = select(Product)
    count_query = select(func.count(Product.id))

    filters = []
    if category_id:
        filters.append(Product.category_id == category_id)
    if is_active is not None:
        filters.append(Product.is_active == is_active)
    if search:
        filters.append(
            (Product.name.ilike(f"%{search}%"))
            | (Product.name_ar.ilike(f"%{search}%"))
            | (Product.sku.ilike(f"%{search}%"))
        )
    if low_stock:
        filters.append(Product.current_stock <= Product.min_stock)

    if filters:
        query = query.filter(*filters)
        count_query = count_query.filter(*filters)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        products=[
            ProductResponse(
                id=p.id, sku=p.sku, name=p.name, name_ar=p.name_ar,
                description=p.description, category_id=p.category_id,
                unit_price=float(p.unit_price), cost_price=float(p.cost_price),
                currency=p.currency, current_stock=p.current_stock,
                min_stock=p.min_stock, max_stock=p.max_stock,
                barcode=p.barcode, is_active=p.is_active, created_at=p.created_at,
            )
            for p in products
        ],
        total=total,
    )


@router.post("/products", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")

    existing = await db.execute(select(Product).filter(Product.sku == product.sku))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="SKU already exists")

    new_product = Product(
        id=str(uuid.uuid4()), sku=product.sku, name=product.name,
        name_ar=product.name_ar, description=product.description,
        category_id=product.category_id, unit_price=product.unit_price,
        cost_price=product.cost_price, currency=product.currency,
        current_stock=0, min_stock=product.min_stock, max_stock=product.max_stock,
        barcode=product.barcode, is_active=product.is_active,
    )
    db.add(new_product)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="inventory",
        entity_type="Product", entity_id=new_product.id,
        entity_name=f"{new_product.sku} - {new_product.name}",
        new_values=new_product.sku, request=request,
    )

    return ProductResponse(
        id=new_product.id, sku=new_product.sku, name=new_product.name,
        name_ar=new_product.name_ar, description=new_product.description,
        category_id=new_product.category_id,
        unit_price=float(new_product.unit_price), cost_price=float(new_product.cost_price),
        currency=new_product.currency, current_stock=new_product.current_stock,
        min_stock=new_product.min_stock, max_stock=new_product.max_stock,
        barcode=new_product.barcode, is_active=new_product.is_active,
        created_at=new_product.created_at,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalar()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=product.id, sku=product.sku, name=product.name,
        name_ar=product.name_ar, description=product.description,
        category_id=product.category_id,
        unit_price=float(product.unit_price), cost_price=float(product.cost_price),
        currency=product.currency, current_stock=product.current_stock,
        min_stock=product.min_stock, max_stock=product.max_stock,
        barcode=product.barcode, is_active=product.is_active,
        created_at=product.created_at,
    )


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:delete" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:delete")

    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalar()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_values = product.sku
    await db.delete(product)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="delete", module="inventory",
        entity_type="Product", entity_id=product_id,
        entity_name=old_values, request=request,
    )

    return {"message": "Product deleted"}


# ─── CATEGORIES ───────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return [CategoryResponse(
        id=c.id, name=c.name, name_ar=c.name_ar,
        parent_id=c.parent_id, created_at=c.created_at,
    ) for c in categories]


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")

    new_cat = Category(
        id=str(uuid.uuid4()), name=category.name,
        name_ar=category.name_ar, parent_id=category.parent_id,
    )
    db.add(new_cat)
    await db.flush()
    return CategoryResponse(
        id=new_cat.id, name=new_cat.name, name_ar=new_cat.name_ar,
        parent_id=new_cat.parent_id, created_at=new_cat.created_at,
    )


# ─── WAREHOUSES ───────────────────────────────────────────

@router.get("/warehouses", response_model=list[WarehouseResponse])
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    result = await db.execute(select(Warehouse))
    warehouses = result.scalars().all()
    return [WarehouseResponse(
        id=w.id, name=w.name, name_ar=w.name_ar, code=w.code,
        address=w.address, is_active=w.is_active, created_at=w.created_at,
    ) for w in warehouses]


@router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    warehouse: WarehouseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")

    new_wh = Warehouse(
        id=str(uuid.uuid4()), name=warehouse.name,
        name_ar=warehouse.name_ar, code=warehouse.code,
        address=warehouse.address, manager_id=warehouse.manager_id,
        is_active=True,
    )
    db.add(new_wh)
    await db.flush()
    return WarehouseResponse(
        id=new_wh.id, name=new_wh.name, name_ar=new_wh.name_ar,
        code=new_wh.code, address=new_wh.address,
        is_active=new_wh.is_active, created_at=new_wh.created_at,
    )


# ─── STOCK MOVEMENTS ─────────────────────────────────────

@router.get("/movements", response_model=StockMovementListResponse)
async def list_movements(
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    query = select(StockMovement)
    count_q = select(func.count(StockMovement.id))

    filters = []
    if product_id:
        filters.append(StockMovement.product_id == product_id)
    if warehouse_id:
        filters.append(StockMovement.warehouse_id == warehouse_id)
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)

    if filters:
        query = query.filter(*filters)
        count_q = count_q.filter(*filters)

    query = query.order_by(StockMovement.created_at.desc())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    movements = result.scalars().all()

    return StockMovementListResponse(
        movements=[
            StockMovementResponse(
                id=m.id, product_id=m.product_id, warehouse_id=m.warehouse_id,
                movement_type=m.movement_type, quantity=m.quantity,
                reference=m.reference, notes=m.notes,
                movement_date=m.movement_date, created_at=m.created_at,
            )
            for m in movements
        ],
        total=total,
    )


@router.post("/movements", response_model=StockMovementResponse)
async def create_movement(
    movement: StockMovementCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")

    new_movement = StockMovement(
        id=str(uuid.uuid4()), product_id=movement.product_id,
        warehouse_id=movement.warehouse_id, movement_type=movement.movement_type,
        quantity=movement.quantity, reference=movement.reference,
        notes=movement.notes, movement_date=movement.movement_date,
    )
    db.add(new_movement)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="inventory",
        entity_type="StockMovement", entity_id=new_movement.id,
        entity_name=f"{movement.movement_type}: {movement.quantity}",
        request=request,
    )

    return StockMovementResponse(
        id=new_movement.id, product_id=new_movement.product_id,
        warehouse_id=new_movement.warehouse_id,
        movement_type=new_movement.movement_type, quantity=new_movement.quantity,
        reference=new_movement.reference, notes=new_movement.notes,
        movement_date=new_movement.movement_date, created_at=new_movement.created_at,
    )


# ─── LOW STOCK ALERTS ────────────────────────────────────

@router.get("/low-stock", response_model=list[LowStockAlert])
async def get_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")

    result = await db.execute(
        select(Product).filter(
            Product.current_stock <= Product.min_stock,
            Product.is_active.is_(True),
        )
    )
    products = result.scalars().all()

    return [
        LowStockAlert(
            product_id=p.id, sku=p.sku, name=p.name, name_ar=p.name_ar,
            current_stock=p.current_stock, min_stock=p.min_stock, warehouse_name=None,
        )
        for p in products
    ]
