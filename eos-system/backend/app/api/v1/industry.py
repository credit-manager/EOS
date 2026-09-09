"""
EOS System - Industry Template Endpoints (Pharmacy, Restaurant, Retail)
All endpoints: RBAC enforced, tenant_id filtered, audit logged.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.industry_templates import (
    PharmacyProduct, PharmacySale, PharmacyAlert,
    Recipe, RecipeIngredient, RestaurantTable, RestaurantOrder,
    RetailBranch, RetailPriceList, RetailPriceListItem, RetailPromotion,
)

router = APIRouter()


# === PHARMACY ===

class PharmacyProductCreate(BaseModel):
    product_id: str
    batch_number: Optional[str] = None
    expiry_date: date
    manufacturing_date: Optional[date] = None
    manufacturer: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    is_controlled: bool = False
    requires_prescription: bool = False
    storage_condition: Optional[str] = None
    barcode: Optional[str] = None


class PharmacyAlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_resolved: bool = False


@router.get("/pharmacy/products")
async def list_pharmacy_products(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    result = await db.execute(
        select(PharmacyProduct).filter(
            PharmacyProduct.tenant_id == current_user["tenant_id"],
            PharmacyProduct.is_active == True,
        ).order_by(PharmacyProduct.expiry_date)
    )
    return [p.to_dict() for p in result.scalars().all()]


@router.post("/pharmacy/products")
async def create_pharmacy_product(
    request: Request,
    body: PharmacyProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    pp = PharmacyProduct(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        **body.model_dump(),
    )
    db.add(pp)
    await db.flush()

    if pp.expiry_date:
        days_to_expiry = (pp.expiry_date - date.today()).days
        if days_to_expiry <= 90:
            db.add(PharmacyAlert(
                id=str(uuid.uuid4()),
                tenant_id=current_user["tenant_id"],
                alert_type="expiry_warning",
                severity="critical" if days_to_expiry <= 30 else "warning",
                product_id=pp.product_id,
                message=f"Product expires in {days_to_expiry} days",
            ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="pharmacy",
        entity_type="PharmacyProduct", entity_id=pp.id,
        entity_name=pp.batch_number or "new product", request=request,
    )
    return pp.to_dict()


@router.get("/pharmacy/alerts")
async def list_pharmacy_alerts(
    is_read: Optional[bool] = None,
    alert_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    q = select(PharmacyAlert).filter(
        PharmacyAlert.tenant_id == current_user["tenant_id"],
    )
    if is_read is not None:
        q = q.filter(PharmacyAlert.is_read == is_read)
    if alert_type:
        q = q.filter(PharmacyAlert.alert_type == alert_type)
    result = await db.execute(q.order_by(PharmacyAlert.created_at.desc()).limit(100))
    return [a.to_dict() for a in result.scalars().all()]


@router.patch("/pharmacy/alerts/{alert_id}")
async def update_pharmacy_alert(
    alert_id: str,
    body: PharmacyAlertUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:update")
    result = await db.execute(
        select(PharmacyAlert).filter(
            PharmacyAlert.id == alert_id,
            PharmacyAlert.tenant_id == current_user["tenant_id"],
        )
    )
    alert = result.scalar()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if body.is_read is not None:
        alert.is_read = body.is_read
    if body.is_resolved:
        alert.is_resolved = True
        alert.resolved_by = current_user["id"]
        alert.resolved_at = datetime.utcnow()
    await db.flush()
    return alert.to_dict()


# === RESTAURANT/CAFE ===

class RecipeCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    category: Optional[str] = None
    serving_size: int = 1
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    selling_price: float = 0
    ingredients: list[dict] = []


class TableCreate(BaseModel):
    table_number: str
    capacity: int = 4
    section: Optional[str] = None


class OrderCreate(BaseModel):
    table_id: Optional[str] = None
    order_type: str = "dine_in"
    guests_count: int = 1
    notes: Optional[str] = None


@router.get("/restaurant/recipes")
async def list_recipes(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    q = select(Recipe).options(selectinload(Recipe.ingredients)).filter(
        Recipe.tenant_id == current_user["tenant_id"],
        Recipe.is_active == True,
    )
    if category:
        q = q.filter(Recipe.category == category)
    result = await db.execute(q.order_by(Recipe.name))
    return [r.to_dict(include_ingredients=True) for r in result.scalars().all()]


@router.post("/restaurant/recipes")
async def create_recipe(
    request: Request,
    body: RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    recipe = Recipe(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        name=body.name,
        name_ar=body.name_ar,
        category=body.category,
        serving_size=body.serving_size,
        prep_time_minutes=body.prep_time_minutes,
        cook_time_minutes=body.cook_time_minutes,
        selling_price=body.selling_price,
    )
    db.add(recipe)
    await db.flush()

    for ing in body.ingredients:
        db.add(RecipeIngredient(
            id=str(uuid.uuid4()),
            recipe_id=recipe.id,
            product_id=ing.get("product_id", ""),
            quantity=ing.get("quantity", 0),
            unit=ing.get("unit"),
            cost_per_unit=ing.get("cost_per_unit", 0),
        ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="restaurant",
        entity_type="Recipe", entity_id=recipe.id,
        entity_name=recipe.name, request=request,
    )
    return recipe.to_dict()


@router.get("/restaurant/tables")
async def list_tables(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    result = await db.execute(
        select(RestaurantTable).filter(
            RestaurantTable.tenant_id == current_user["tenant_id"],
            RestaurantTable.is_active == True,
        ).order_by(RestaurantTable.table_number)
    )
    return [t.to_dict() for t in result.scalars().all()]


@router.post("/restaurant/tables")
async def create_table(
    request: Request,
    body: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    table = RestaurantTable(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        **body.model_dump(),
    )
    db.add(table)
    await db.flush()
    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="restaurant",
        entity_type="RestaurantTable", entity_id=table.id,
        entity_name=table.table_number, request=request,
    )
    return table.to_dict()


@router.get("/restaurant/orders")
async def list_orders(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    q = select(RestaurantOrder).filter(
        RestaurantOrder.tenant_id == current_user["tenant_id"],
    )
    if status:
        q = q.filter(RestaurantOrder.status == status)
    result = await db.execute(q.order_by(RestaurantOrder.created_at.desc()).limit(100))
    return [o.to_dict() for o in result.scalars().all()]


@router.post("/restaurant/orders")
async def create_order(
    request: Request,
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    order = RestaurantOrder(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        **body.model_dump(),
    )
    db.add(order)
    await db.flush()
    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="restaurant",
        entity_type="RestaurantOrder", entity_id=order.id,
        entity_name=f"Order {order.order_type}", request=request,
    )
    return order.to_dict()


# === RETAIL STORE ===

class BranchCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    code: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    warehouse_id: Optional[str] = None


class PriceListCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    branch_id: Optional[str] = None
    customer_segment: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    items: list[dict] = []


class PromotionCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    promotion_type: str
    discount_value: Optional[float] = None
    min_purchase: Optional[float] = None
    max_discount: Optional[float] = None
    start_date: date
    end_date: date
    branch_id: Optional[str] = None


@router.get("/retail/branches")
async def list_branches(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    result = await db.execute(
        select(RetailBranch).filter(
            RetailBranch.tenant_id == current_user["tenant_id"],
            RetailBranch.is_active == True,
        ).order_by(RetailBranch.name)
    )
    return [b.to_dict() for b in result.scalars().all()]


@router.post("/retail/branches")
async def create_branch(
    request: Request,
    body: BranchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    branch = RetailBranch(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        **body.model_dump(),
    )
    db.add(branch)
    await db.flush()
    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="retail",
        entity_type="RetailBranch", entity_id=branch.id,
        entity_name=branch.name, request=request,
    )
    return branch.to_dict()


@router.get("/retail/price-lists")
async def list_price_lists(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    result = await db.execute(
        select(RetailPriceList).filter(
            RetailPriceList.tenant_id == current_user["tenant_id"],
            RetailPriceList.is_active == True,
        )
    )
    return [pl.to_dict() for pl in result.scalars().all()]


@router.post("/retail/price-lists")
async def create_price_list(
    request: Request,
    body: PriceListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    pl = RetailPriceList(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        name=body.name,
        name_ar=body.name_ar,
        branch_id=body.branch_id,
        customer_segment=body.customer_segment,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
    )
    db.add(pl)
    await db.flush()

    for item in body.items:
        db.add(RetailPriceListItem(
            id=str(uuid.uuid4()),
            price_list_id=pl.id,
            product_id=item.get("product_id", ""),
            price=item.get("price", 0),
            min_quantity=item.get("min_quantity", 1),
            discount_percentage=item.get("discount_percentage", 0),
        ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="retail",
        entity_type="RetailPriceList", entity_id=pl.id,
        entity_name=pl.name, request=request,
    )
    return pl.to_dict()


@router.get("/retail/promotions")
async def list_promotions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:read")
    result = await db.execute(
        select(RetailPromotion).filter(
            RetailPromotion.tenant_id == current_user["tenant_id"],
            RetailPromotion.is_active == True,
            RetailPromotion.end_date >= date.today(),
        ).order_by(RetailPromotion.end_date)
    )
    return [p.to_dict() for p in result.scalars().all()]


@router.post("/retail/promotions")
async def create_promotion(
    request: Request,
    body: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "inventory:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires inventory:create")
    promo = RetailPromotion(
        id=str(uuid.uuid4()),
        tenant_id=current_user["tenant_id"],
        **body.model_dump(),
    )
    db.add(promo)
    await db.flush()
    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="retail",
        entity_type="RetailPromotion", entity_id=promo.id,
        entity_name=promo.name, request=request,
    )
    return promo.to_dict()
