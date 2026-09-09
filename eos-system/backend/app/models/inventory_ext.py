"""
EOS System — Extended Inventory Models (Units, Product Variants, Stock Takes, BOMs)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class UnitOfMeasure(Base):
    """Unit of Measure (piece, kg, meter, etc.)."""
    
    __tablename__ = "units"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    name_ar = Column(String(50))
    symbol = Column(String(10), nullable=False)
    base_unit_id = Column(String(36), ForeignKey("units.id"))
    conversion_factor = Column(Numeric(10, 4), default=1)
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "symbol": self.symbol}


class ProductVariant(Base):
    """Product Variant (size, color, etc.)."""
    
    __tablename__ = "product_variants"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(18, 2), nullable=False)
    cost = Column(Numeric(18, 2), default=0)
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product")
    
    def to_dict(self):
        return {"id": self.id, "sku": self.sku, "name": self.name, "price": float(self.price)}


class StockTake(Base):
    """Physical Stock Count / Inventory Audit."""
    
    __tablename__ = "stock_takes"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    reference = Column(String(50), unique=True, nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False)
    status = Column(String(20), default="draft", index=True)  # draft, in_progress, completed
    notes = Column(Text)
    completed_at = Column(DateTime)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    warehouse = relationship("Warehouse")
    items = relationship("StockTakeItem", back_populates="stock_take", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {"id": self.id, "reference": self.reference, "status": self.status}


class StockTakeItem(Base):
    """Stock Take Line Item."""
    
    __tablename__ = "stock_take_lines"
    
    id = Column(String(36), primary_key=True)
    stock_take_id = Column(String(36), ForeignKey("stock_takes.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    system_quantity = Column(Integer, nullable=False)
    counted_quantity = Column(Integer)
    variance = Column(Integer)
    notes = Column(Text)
    
    stock_take = relationship("StockTake", back_populates="items")
    product = relationship("Product")


class BillOfMaterials(Base):
    """Bill of Materials (BOM) for manufacturing."""
    
    __tablename__ = "boms"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product")
    items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "product_id": self.product_id}


class BOMItem(Base):
    """BOM Component / Raw Material."""
    
    __tablename__ = "bom_lines"
    
    id = Column(String(36), primary_key=True)
    bom_id = Column(String(36), ForeignKey("boms.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit_cost = Column(Numeric(18, 2), default=0)
    
    bom = relationship("BillOfMaterials", back_populates="items")
    product = relationship("Product")
