"""
EOS System — Industry Template Models (Pharmacy, Restaurant, Retail)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


# ═══════════════════════════════════════════════════════════
# PHARMACY TEMPLATE
# ═══════════════════════════════════════════════════════════

class PharmacyProduct(Base):
    """Pharmacy-specific product attributes — expiry, batch, controlled substance."""

    __tablename__ = "pharmacy_products"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    batch_number = Column(String(100), index=True)
    expiry_date = Column(Date, nullable=False, index=True)
    manufacturing_date = Column(Date)
    manufacturer = Column(String(255))
    manufacturer_ar = Column(String(255))
    strength = Column(String(100))  # e.g. "500mg", "10ml"
    dosage_form = Column(String(50))  # tablet, capsule, syrup, injection
    is_controlled = Column(Boolean, default=False)  # controlled substance
    controlled_schedule = Column(String(20))  # Schedule II, III, IV, V
    requires_prescription = Column(Boolean, default=False)
    storage_condition = Column(String(100))  # room temp, cold chain, refrigerated
    barcode = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "batch_number": self.batch_number,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "strength": self.strength,
            "dosage_form": self.dosage_form,
            "is_controlled": self.is_controlled,
            "requires_prescription": self.requires_prescription,
        }


class PharmacySale(Base):
    """Pharmacy sale — tracks prescription-linked sales."""

    __tablename__ = "pharmacy_sales"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    sale_id = Column(String(36), ForeignKey("sales_orders.id"))
    patient_name = Column(String(255))
    patient_name_ar = Column(String(255))
    doctor_name = Column(String(255))
    prescription_number = Column(String(100))
    prescription_image_url = Column(String(500))
    dispensing_pharmacist = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "doctor_name": self.doctor_name,
            "prescription_number": self.prescription_number,
        }


class PharmacyAlert(Base):
    """Pharmacy alerts — expiry warnings, low stock, controlled substance tracking."""

    __tablename__ = "pharmacy_alerts"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # expiry_warning, low_stock, controlled_usage, recall
    severity = Column(String(20), default="info")  # info, warning, critical
    product_id = Column(String(36), ForeignKey("products.id"))
    message = Column(Text)
    message_ar = Column(Text)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(36), ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "is_read": self.is_read,
        }


# ═══════════════════════════════════════════════════════════
# RESTAURANT/CAFE TEMPLATE
# ═══════════════════════════════════════════════════════════

class Recipe(Base):
    """Recipe — defines dish composition and costing."""

    __tablename__ = "recipes"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    category = Column(String(100))  # appetizer, main, dessert, beverage
    serving_size = Column(Integer, default=1)
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    selling_price = Column(Numeric(18, 2))
    cost_price = Column(Numeric(18, 2))
    profit_margin = Column(Numeric(5, 2))  # percentage
    image_url = Column(String(500))
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

    def to_dict(self, include_ingredients=False):
        data = {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "category": self.category,
            "selling_price": float(self.selling_price) if self.selling_price else 0,
            "cost_price": float(self.cost_price) if self.cost_price else 0,
            "profit_margin": float(self.profit_margin) if self.profit_margin else 0,
            "is_available": self.is_available,
        }
        if include_ingredients:
            data["ingredients"] = [i.to_dict() for i in self.ingredients]
        return data


class RecipeIngredient(Base):
    """Recipe Ingredient — links recipe to products with quantities."""

    __tablename__ = "recipe_ingredients"

    id = Column(String(36), primary_key=True)
    recipe_id = Column(String(36), ForeignKey("recipes.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20))  # g, ml, piece, tbsp
    cost_per_unit = Column(Numeric(18, 2))
    is_optional = Column(Boolean, default=False)
    notes = Column(Text)

    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": float(self.quantity),
            "unit": self.unit,
            "cost_per_unit": float(self.cost_per_unit) if self.cost_per_unit else 0,
        }


class RestaurantTable(Base):
    """Restaurant Table — for dine-in management."""

    __tablename__ = "restaurant_tables"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    table_number = Column(String(20), nullable=False)
    capacity = Column(Integer, default=4)
    section = Column(String(50))  # indoor, outdoor, VIP
    status = Column(String(20), default="available")  # available, occupied, reserved, cleaning
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "table_number": self.table_number,
            "capacity": self.capacity,
            "section": self.section,
            "status": self.status,
        }


class RestaurantOrder(Base):
    """Restaurant Order — links to sales_orders with restaurant-specific fields."""

    __tablename__ = "restaurant_orders"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"))
    table_id = Column(String(36), ForeignKey("restaurant_tables.id"))
    order_type = Column(String(20), default="dine_in")  # dine_in, takeaway, delivery
    guests_count = Column(Integer, default=1)
    status = Column(String(20), default="pending")  # pending, preparing, served, completed
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "order_type": self.order_type,
            "guests_count": self.guests_count,
            "status": self.status,
        }


# ═══════════════════════════════════════════════════════════
# RETAIL STORE TEMPLATE
# ═══════════════════════════════════════════════════════════

class RetailBranch(Base):
    """Retail Branch — multi-location support."""

    __tablename__ = "retail_branches"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    code = Column(String(50), unique=True, nullable=False)
    address = Column(Text)
    city = Column(String(100))
    phone = Column(String(50))
    manager_id = Column(String(36), ForeignKey("users.id"))
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "city": self.city,
            "is_active": self.is_active,
        }


class RetailPriceList(Base):
    """Retail Price List — different prices per branch or customer segment."""

    __tablename__ = "retail_price_lists"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    branch_id = Column(String(36), ForeignKey("retail_branches.id"))
    customer_segment = Column(String(50))  # retail, wholesale, vip
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    valid_from = Column(Date)
    valid_to = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("RetailPriceListItem", back_populates="price_list", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "name": self.name,
            "branch_id": self.branch_id,
            "customer_segment": self.customer_segment,
            "is_default": self.is_default,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class RetailPriceListItem(Base):
    """Price List Item — product price override."""

    __tablename__ = "retail_price_list_items"

    id = Column(String(36), primary_key=True)
    price_list_id = Column(String(36), ForeignKey("retail_price_lists.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    price = Column(Numeric(18, 2), nullable=False)
    min_quantity = Column(Integer, default=1)
    discount_percentage = Column(Numeric(5, 2), default=0)

    price_list = relationship("RetailPriceList", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "price": float(self.price),
            "min_quantity": self.min_quantity,
        }


class RetailPromotion(Base):
    """Retail Promotion — discounts and campaigns."""

    __tablename__ = "retail_promotions"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    promotion_type = Column(String(50), nullable=False)  # percentage, fixed, buy_x_get_y, bundle
    discount_value = Column(Numeric(18, 2))
    min_purchase = Column(Numeric(18, 2))
    max_discount = Column(Numeric(18, 2))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    branch_id = Column(String(36), ForeignKey("retail_branches.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "discount_value": float(self.discount_value) if self.discount_value else 0,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }
