"""
نماذج قاعدة البيانات الأساسية
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, Date
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """نموذج المستخدم"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # علاقات
    roles = relationship("Role", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Role(Base):
    """نموذج الدور والصلاحيات"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(Text)  # JSON string
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="roles")


class Customer(Base):
    """نموذج العميل"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    address = Column(Text)
    city = Column(String)
    country = Column(String)
    tax_number = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # علاقات
    orders = relationship("SalesOrder", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class Supplier(Base):
    """نموذج المورد"""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    address = Column(Text)
    city = Column(String)
    country = Column(String)
    tax_number = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # علاقات
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class Product(Base):
    """نموذج المنتج"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    unit_price = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    quantity = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    unit_of_measure = Column(String, default="piece")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # علاقات
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")


class Category(Base):
    """نموذج التصنيف"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="category")


class SalesOrder(Base):
    """نموذج طلب المبيعات"""
    __tablename__ = "sales_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_date = Column(Date, default=datetime.utcnow)
    delivery_date = Column(Date)
    status = Column(String, default="pending")  # pending, confirmed, shipped, delivered, cancelled
    total_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """نموذج صنف الطلب"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Invoice(Base):
    """نموذج الفاتورة"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_id = Column(Integer, ForeignKey("sales_orders.id"))
    invoice_date = Column(Date, default=datetime.utcnow)
    due_date = Column(Date)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    status = Column(String, default="unpaid")  # unpaid, partial, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="invoices")


class PurchaseOrder(Base):
    """نموذج أمر الشراء"""
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    order_date = Column(Date, default=datetime.utcnow)
    expected_date = Column(Date)
    status = Column(String, default="pending")  # pending, approved, received, cancelled
    total_amount = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    supplier = relationship("Supplier", back_populates="purchase_orders")


class StockMovement(Base):
    """نموذج حركة المخزون"""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    movement_type = Column(String, nullable=False)  # in, out, transfer, adjustment
    quantity = Column(Integer, nullable=False)
    reference_type = Column(String)  # order, purchase, adjustment
    reference_id = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="stock_movements")


class Employee(Base):
    """نموذج الموظف"""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_number = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    department = Column(String)
    position = Column(String)
    hire_date = Column(Date)
    salary = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """نموذج سجل التدقيق"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(Integer)
    old_value = Column(Text)  # JSON
    new_value = Column(Text)  # JSON
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")
