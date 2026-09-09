"""
EOS System — Inventory Models
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Category(Base):
    """Product Category model."""
    
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    parent_id = Column(String(36), ForeignKey("categories.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")
    
    def __repr__(self):
        return f"<Category {self.name}>"
    
    def to_dict(self, include_children=False):
        data = {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "parent_id": self.parent_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_children:
            data["children"] = [child.to_dict() for child in self.children]
        
        return data


class Product(Base):
    """Product model."""
    
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(String(36), ForeignKey("categories.id"), index=True)
    unit_price = Column(Numeric(18, 2), nullable=False)
    cost_price = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default="EGP")
    current_stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=0)
    max_stock = Column(Integer)
    barcode = Column(String(100), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    stock_movements = relationship("StockMovement", back_populates="product")
    
    def __repr__(self):
        return f"<Product {self.sku} - {self.name}>"
    
    def to_dict(self, include_category=False):
        data = {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "category_id": self.category_id,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "cost_price": float(self.cost_price) if self.cost_price else 0,
            "currency": self.currency,
            "current_stock": self.current_stock,
            "min_stock": self.min_stock,
            "max_stock": self.max_stock,
            "barcode": self.barcode,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_category and self.category:
            data["category"] = self.category.to_dict()
        
        return data
    
    @property
    def is_low_stock(self):
        """Check if product is below minimum stock level."""
        return self.current_stock <= self.min_stock
    
    @property
    def is_out_of_stock(self):
        """Check if product is out of stock."""
        return self.current_stock <= 0


class Warehouse(Base):
    """Warehouse model."""
    
    __tablename__ = "warehouses"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    address = Column(String(500))
    address_ar = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock_movements = relationship("StockMovement", back_populates="warehouse")
    
    def __repr__(self):
        return f"<Warehouse {self.code} - {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "name_ar": self.name_ar,
            "address": self.address,
            "address_ar": self.address_ar,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StockMovement(Base):
    """Stock Movement model."""
    
    __tablename__ = "stock_movements"
    
    id = Column(String(36), primary_key=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False, index=True)  # in, out, transfer, adjustment
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(18, 2))
    reference = Column(String(100))
    notes = Column(Text)
    movement_date = Column(Date, nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="stock_movements")
    warehouse = relationship("Warehouse", back_populates="stock_movements")
    
    def __repr__(self):
        return f"<StockMovement {self.movement_type} - {self.product_id}>"
    
    def to_dict(self, include_product=False, include_warehouse=False):
        data = {
            "id": self.id,
            "product_id": self.product_id,
            "warehouse_id": self.warehouse_id,
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "unit_cost": float(self.unit_cost) if self.unit_cost else None,
            "total_cost": float(self.unit_cost * self.quantity) if self.unit_cost else None,
            "reference": self.reference,
            "notes": self.notes,
            "movement_date": self.movement_date.isoformat() if self.movement_date else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_product and self.product:
            data["product"] = self.product.to_dict()
        
        if include_warehouse and self.warehouse:
            data["warehouse"] = self.warehouse.to_dict()
        
        return data
