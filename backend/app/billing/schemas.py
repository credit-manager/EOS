"""Pydantic schemas for billing endpoints."""
from datetime import datetime
from pydantic import BaseModel


class PlanOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    price_monthly: float
    price_yearly: float | None
    max_users: int
    max_storage_gb: int
    features: str | None


class SubscriptionOut(BaseModel):
    id: str | None = None
    status: str
    billing_cycle: str | None = None
    current_period_end: str | None = None
    trial_end: str | None = None
    plan: dict | None = None


class SubscribeRequest(BaseModel):
    plan_code: str
    billing_cycle: str = "monthly"


class SubscribeResponse(BaseModel):
    subscription_id: str
    status: str


class CancelResponse(BaseModel):
    status: str
    end_date: str
