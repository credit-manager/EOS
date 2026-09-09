"""
EOS System — Sales & CRM Models
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Customer(Base):
    """Customer model."""
    
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    type = Column(String(20), default="individual", index=True)
    email = Column(String(255), index=True)
    phone = Column(String(50))
    address = Column(String(500))
    tax_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    total_orders = Column(Integer, default=0)
    total_spent = Column(Numeric(18, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunities = relationship("Opportunity", back_populates="customer")
    quotes = relationship("Quote", back_populates="customer")
    eta_invoices = relationship(
        "EtaInvoice",
        back_populates="buyer",
    )
    
    def __repr__(self):
        return f"<Customer {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "type": self.type,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "tax_id": self.tax_id,
            "total_orders": self.total_orders,
            "total_spent": float(self.total_spent) if self.total_spent else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Lead(Base):
    """Lead model."""
    
    __tablename__ = "leads"
    
    id = Column(String(36), primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company_name = Column(String(255))
    email = Column(String(255), index=True)
    phone = Column(String(50))
    source = Column(String(50), index=True)  # website, referral, cold_call, etc.
    status = Column(String(20), default="new", index=True)  # new, contacted, qualified, unqualified
    score = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunities = relationship("Opportunity", back_populates="lead")
    
    def __repr__(self):
        return f"<Lead {self.first_name} {self.last_name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "source": self.source,
            "status": self.status,
            "score": self.score,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Opportunity(Base):
    """Opportunity model."""
    
    __tablename__ = "opportunities"
    
    id = Column(String(36), primary_key=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), index=True)
    name = Column(String(255), nullable=False)
    stage = Column(String(50), default="qualification", index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default="EGP")
    expected_close_date = Column(Date)
    probability = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lead = relationship("Lead", back_populates="opportunities")
    customer = relationship("Customer", back_populates="opportunities")
    quotes = relationship("Quote", back_populates="opportunity")
    
    def __repr__(self):
        return f"<Opportunity {self.name}>"
    
    def to_dict(self, include_lead=False, include_customer=False):
        data = {
            "id": self.id,
            "lead_id": self.lead_id,
            "customer_id": self.customer_id,
            "name": self.name,
            "stage": self.stage,
            "amount": float(self.amount) if self.amount else 0,
            "currency": self.currency,
            "expected_close_date": self.expected_close_date.isoformat() if self.expected_close_date else None,
            "probability": self.probability,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_lead and self.lead:
            data["lead"] = self.lead.to_dict()
        
        if include_customer and self.customer:
            data["customer"] = self.customer.to_dict()
        
        return data


class Quote(Base):
    """Quote model."""
    
    __tablename__ = "quotes"
    
    id = Column(String(36), primary_key=True)
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    status = Column(String(20), default="draft", index=True)  # draft, sent, accepted, rejected, expired
    total_amount = Column(Numeric(18, 2), default=0)
    valid_until = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="quotes")
    customer = relationship("Customer", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Quote {self.quote_number}>"
    
    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "quote_number": self.quote_number,
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "status": self.status,
            "total_amount": float(self.total_amount) if self.total_amount else 0,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        
        return data
    
    def calculate_total(self):
        """Calculate total amount from items."""
        total = sum(item.quantity * item.unit_price for item in self.items)
        self.total_amount = total
        return total


class QuoteItem(Base):
    """Quote Item model."""
    
    __tablename__ = "quote_items"
    
    id = Column(String(36), primary_key=True)
    quote_id = Column(String(36), ForeignKey("quotes.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quote = relationship("Quote", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<QuoteItem {self.id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "quote_id": self.quote_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "discount_percent": float(self.discount_percent) if self.discount_percent else 0,
            "total": float(self.quantity * self.unit_price * (1 - (self.discount_percent or 0) / 100)),
        }
