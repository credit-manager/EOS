"""
EOS System — API Router
"""
from fastapi import APIRouter
from app.api.v1 import (
    auth, tenants, users, accounting, inventory, hr, sales, projects,
    invoices, banking, infrastructure, industry,
)
from app.api.v1.ai_router import ai_router

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Core ERP Modules
api_router.include_router(accounting.router, prefix="/{tenant_id}/accounting", tags=["Accounting"])
api_router.include_router(inventory.router, prefix="/{tenant_id}/inventory", tags=["Inventory"])
api_router.include_router(hr.router, prefix="/{tenant_id}/hr", tags=["Human Resources"])
api_router.include_router(sales.router, prefix="/{tenant_id}/sales", tags=["Sales & CRM"])
api_router.include_router(projects.router, prefix="/{tenant_id}/projects", tags=["Projects"])

# Invoices (Sales + Supplier)
api_router.include_router(invoices.router, prefix="/{tenant_id}/sales", tags=["Invoices"])

# Bank Reconciliation & Statements
api_router.include_router(banking.router, prefix="/{tenant_id}/accounting", tags=["Banking & Statements"])

# Infrastructure (Fiscal Years, Currencies, Company Profile)
api_router.include_router(infrastructure.router, prefix="/{tenant_id}/infrastructure", tags=["Infrastructure"])

# AI Layer (Copilot, Prediction, OCR, Onboarding)
api_router.include_router(ai_router, prefix="/{tenant_id}/ai", tags=["AI Layer"])

# Industry Templates (Pharmacy, Restaurant, Retail)
api_router.include_router(industry.router, prefix="/{tenant_id}/industry", tags=["Industry Templates"])
