"""Billing models — plans, subscriptions, invoices."""
from datetime import datetime, UTC
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean
from ..db import Base

class Plan(Base):
    __tablename__ = "billing_plans"
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float)
    max_users = Column(Integer, default=10)
    max_storage_gb = Column(Integer, default=5)
    features = Column(Text)  # JSON list of features
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class Subscription(Base):
    __tablename__ = "billing_subscriptions"
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    plan_id = Column(String(36), nullable=False)
    status = Column(String(20), default="active")  # active, past_due, canceled, trialing
    billing_cycle = Column(String(10), default="monthly")  # monthly, yearly
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    trial_end = Column(DateTime)
    stripe_subscription_id = Column(String(200), nullable=True, index=True)
    stripe_customer_id = Column(String(200), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class Invoice(Base):
    __tablename__ = "billing_invoices"
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    subscription_id = Column(String(36), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="pending")  # pending, paid, failed, void
    billing_reason = Column(String(50))  # subscription_create, subscription_cycle, subscription_update
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
