"""
EOS System — Extended Sales & Purchase Models (Suppliers, POs, SOs, Invoices, Opportunity Stages)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Supplier(Base):
    """Supplier / Vendor."""
    
    __tablename__ = "suppliers"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    code = Column(String(50), unique=True, nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    tax_number = Column(String(50))
    payment_terms = Column(Integer, default=30)  # days
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    eta_invoices = relationship(
        "EtaInvoice", back_populates="supplier"
    )
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "code": self.code}


class PurchaseOrder(Base):
    """Purchase Order."""
    
    __tablename__ = "purchase_orders"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    expected_date = Column(Date)
    status = Column(String(20), default="draft", index=True)  # draft, sent, received, cancelled
    subtotal = Column(Numeric(18, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), default=0)
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    
    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "order_number": self.order_number,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "status": self.status,
            "total": float(self.total) if self.total else 0,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class PurchaseOrderItem(Base):
    """Purchase Order Line Item."""
    
    __tablename__ = "purchase_order_lines"
    
    id = Column(String(36), primary_key=True)
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    total = Column(Numeric(18, 2), nullable=False)
    received_quantity = Column(Integer, default=0)
    
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total),
        }


class SalesOrder(Base):
    """Sales Order / Invoice."""
    
    __tablename__ = "sales_orders"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    due_date = Column(Date)
    status = Column(String(20), default="draft", index=True)  # draft, confirmed, delivered, cancelled
    subtotal = Column(Numeric(18, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), default=0)
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    
    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "status": self.status,
            "total": float(self.total) if self.total else 0,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class SalesOrderItem(Base):
    """Sales Order Line Item."""
    
    __tablename__ = "sales_order_lines"
    
    id = Column(String(36), primary_key=True)
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), nullable=False)
    
    sales_order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total),
        }


class CustomerPayment(Base):
    """Customer Payment Receipt."""
    
    __tablename__ = "customer_payments"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    reference = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"))
    amount = Column(Numeric(18, 2), nullable=False)
    payment_method = Column(String(50))  # cash, bank_transfer, check, card
    payment_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer")
    sales_order = relationship("SalesOrder")
    
    def to_dict(self):
        return {"id": self.id, "reference": self.reference, "amount": float(self.amount), "payment_method": self.payment_method}


class SupplierPayment(Base):
    """Supplier Payment."""
    
    __tablename__ = "supplier_payments"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    reference = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False, index=True)
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id"))
    amount = Column(Numeric(18, 2), nullable=False)
    payment_method = Column(String(50))
    payment_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    
    def to_dict(self):
        return {"id": self.id, "reference": self.reference, "amount": float(self.amount)}


class SalesInvoice(Base):
    """Sales Invoice — billed amount to customer."""

    __tablename__ = "sales_invoices"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"))
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    status = Column(String(20), default="draft", index=True)  # draft, sent, paid, overdue, void
    subtotal = Column(Numeric(18, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    discount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), default=0)
    amount_paid = Column(Numeric(18, 2), default=0)
    currency = Column(String(3), default="EGP")
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer")
    sales_order = relationship("SalesOrder")
    items = relationship("SalesInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "total": float(self.total) if self.total else 0,
            "amount_paid": float(self.amount_paid) if self.amount_paid else 0,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class SalesInvoiceLine(Base):
    """Sales Invoice Line Item."""

    __tablename__ = "sales_invoice_lines"

    id = Column(String(36), primary_key=True)
    invoice_id = Column(String(36), ForeignKey("sales_invoices.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"))
    description = Column(String(500))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), nullable=False)

    invoice = relationship("SalesInvoice", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total),
        }


class SupplierInvoice(Base):
    """Supplier Invoice — billed amount from supplier."""

    __tablename__ = "supplier_invoices"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False, index=True)
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id"))
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    status = Column(String(20), default="draft", index=True)  # draft, approved, paid, overdue, void
    subtotal = Column(Numeric(18, 2), default=0)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), default=0)
    amount_paid = Column(Numeric(18, 2), default=0)
    currency = Column(String(3), default="EGP")
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    items = relationship("SupplierInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "status": self.status,
            "total": float(self.total) if self.total else 0,
            "amount_paid": float(self.amount_paid) if self.amount_paid else 0,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class SupplierInvoiceLine(Base):
    """Supplier Invoice Line Item."""

    __tablename__ = "supplier_invoice_lines"

    id = Column(String(36), primary_key=True)
    invoice_id = Column(String(36), ForeignKey("supplier_invoices.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"))
    description = Column(String(500))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    tax_amount = Column(Numeric(18, 2), default=0)
    total = Column(Numeric(18, 2), nullable=False)

    invoice = relationship("SupplierInvoice", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total),
        }


class OpportunityStage(Base):
    """Opportunity Stage — defines CRM pipeline stages."""

    __tablename__ = "opportunity_stages"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    sort_order = Column(Integer, default=0)
    probability = Column(Integer, default=0)  # 0-100
    is_won = Column(Boolean, default=False)
    is_lost = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "sort_order": self.sort_order,
            "probability": self.probability,
            "is_won": self.is_won,
            "is_lost": self.is_lost,
        }
