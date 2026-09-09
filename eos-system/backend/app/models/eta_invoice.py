"""
EOS System — Egyptian E-Invoice Model (ETA Compliance)
يمثل نموذج الفاتورة المصرية conforms لمواصفات الهيئة المصرية للزكاء والضريبة.
"""
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class EtaInvoice(Base):
    """Main ETA Egyptian Invoice Table."""
    __tablename__ = "eta_invoices"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Basic invoice info
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    
    # Supplier (seller)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False, index=True)
    supplier_name_ar = Column(String(255), nullable=False)
    supplier_name_en = Column(String(255))
    
    # Buyer (customer)
    buyer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    buyer_name_ar = Column(String(255), nullable=False)
    buyer_name_en = Column(String(255))
    
    # Invoice totals
    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(18, 2), nullable=False, default=0)  # 14% VAT
    total_amount = Column(Numeric(18, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="EGP")
    
    # ETA specific fields
    eta_status = Column(String(20), default="pending")  # pending, validated, rejected
    eta_validation_date = Column(DateTime)
    eta_error_details = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="eta_invoices")
    buyer = relationship("Customer", back_populates="eta_invoices")
    lines = relationship("EtaInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "supplier_id": self.supplier_id,
            "supplier_name_ar": self.supplier_name_ar,
            "buyer_id": self.buyer_id,
            "buyer_name_ar": self.buyer_name_ar,
            "subtotal": float(self.subtotal) if self.subtotal else 0,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0,
            "total_amount": float(self.total_amount) if self.total_amount else 0,
            "currency": self.currency,
            "eta_status": self.eta_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def calculate_tax(self):
        """Calculate 14% VAT automatically."""
        self.tax_amount = round(self.subtotal * 0.14, 2)
        self.total_amount = round(self.subtotal + self.tax_amount, 2)


class EtaInvoiceLine(Base):
    """Line items for ETA Egyptian Invoice."""
    __tablename__ = "eta_invoice_lines"
    
    id = Column(String(36), primary_key=True)
    invoice_id = Column(String(36), ForeignKey("eta_invoices.id"), nullable=False, index=True)
    
    # Product/service info
    product_id = Column(String(36), ForeignKey("products.id"))
    product_name_ar = Column(String(255))
    product_name_en = Column(String(255))
    
    # Line details
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    total_price = Column(Numeric(18, 2), nullable=False)
    
    # Tax per line
    line_tax_amount = Column(Numeric(18, 2), default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("EtaInvoice", back_populates="lines")
    product = relationship("Product")
    
    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "total_price": float(self.total_price) if self.total_price else 0,
            "line_tax_amount": float(self.line_tax_amount) if self.line_tax_amount else 0,
        }