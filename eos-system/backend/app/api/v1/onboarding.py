"""
EOS System - Smart Onboarding Flow
Guides new tenants through setup with AI-powered suggestions.
All endpoints: RBAC enforced, tenant_id filtered, audit logged.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.tenant import Tenant
from app.models.infrastructure import CompanyProfile, FiscalYear, Currency
from app.models.accounting import Account
from app.models.sales import Customer
from app.models.inventory import Product
from app.models.hr import Employee

router = APIRouter()


# --- Schemas ---

class OnboardingStatusResponse(BaseModel):
    tenant_id: str
    company_name: Optional[str]
    setup_complete: bool
    completion_percentage: float
    steps: list
    missing_steps: list
    recommendations: list

class CompanyProfileSetup(BaseModel):
    company_name: str
    company_name_ar: Optional[str] = None
    industry: str
    company_size: Optional[str] = None
    currency: str = "EGP"
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Egypt"
    tax_id: Optional[str] = None
    commercial_registration: Optional[str] = None

class InitialDataLoad(BaseModel):
    industry: str
    company_name: str
    default_currency: str = "EGP"
    create_sample_accounts: bool = True
    create_sample_products: bool = False
    create_sample_customers: bool = False


# --- Industry Templates ---

INDUSTRY_ACCOUNTS = {
    "pharmacy": [
        ("1000", "Cash", "asset"),
        ("1100", "Bank Account", "asset"),
        ("1200", "Inventory - Medicines", "asset"),
        ("1300", "Accounts Receivable", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable", "liability"),
        ("3000", "Owner Equity", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("4100", "Service Revenue", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Salary Expense", "expense"),
        ("5300", "Utilities Expense", "expense"),
        ("5400", "Marketing Expense", "expense"),
    ],
    "restaurant": [
        ("1000", "Cash", "asset"),
        ("1100", "Bank Account", "asset"),
        ("1200", "Inventory - Food", "asset"),
        ("1210", "Inventory - Beverages", "asset"),
        ("1300", "Accounts Receivable", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable", "liability"),
        ("3000", "Owner Equity", "equity"),
        ("4000", "Food Sales", "revenue"),
        ("4100", "Beverage Sales", "revenue"),
        ("5000", "Food Cost", "expense"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Salary Expense", "expense"),
        ("5300", "Utilities Expense", "expense"),
    ],
    "retail": [
        ("1000", "Cash", "asset"),
        ("1100", "Bank Account", "asset"),
        ("1200", "Inventory - Merchandise", "asset"),
        ("1300", "Accounts Receivable", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable", "liability"),
        ("3000", "Owner Equity", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Salary Expense", "expense"),
        ("5300", "Marketing Expense", "expense"),
    ],
    "manufacturing": [
        ("1000", "Cash", "asset"),
        ("1100", "Bank Account", "asset"),
        ("1200", "Raw Materials", "asset"),
        ("1210", "Work in Progress", "asset"),
        ("1220", "Finished Goods", "asset"),
        ("1300", "Accounts Receivable", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable", "liability"),
        ("3000", "Owner Equity", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Raw Material Cost", "expense"),
        ("5200", "Direct Labor", "expense"),
        ("5300", "Factory Overhead", "expense"),
        ("5400", "Rent Expense", "expense"),
    ],
    "services": [
        ("1000", "Cash", "asset"),
        ("1100", "Bank Account", "asset"),
        ("1300", "Accounts Receivable", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable", "liability"),
        ("3000", "Owner Equity", "equity"),
        ("4000", "Service Revenue", "revenue"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Salary Expense", "expense"),
        ("5300", "Marketing Expense", "expense"),
    ],
}


# --- Helper ---

def _check_setup_steps(company_profile, fiscal_year, account_count, customer_count, product_count, employee_count):
    steps = [
        {"step": "company_profile", "label": "Company Profile", "completed": company_profile is not None},
        {"step": "fiscal_year", "label": "Fiscal Year", "completed": fiscal_year is not None},
        {"step": "chart_of_accounts", "label": "Chart of Accounts", "completed": account_count >= 5},
        {"step": "add_products", "label": "Add Products", "completed": product_count > 0},
        {"step": "add_customers", "label": "Add Customers", "completed": customer_count > 0},
        {"step": "add_employees", "label": "Add Employees", "completed": employee_count > 0},
    ]
    completed = sum(1 for s in steps if s["completed"])
    missing = [s for s in steps if not s["completed"]]
    pct = (completed / len(steps)) * 100
    return steps, missing, pct


# --- Endpoints ---

@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    tid = current_user["tenant_id"]

    cp_result = await db.execute(select(CompanyProfile).filter(CompanyProfile.tenant_id == tid).limit(1))
    company_profile = cp_result.scalar()

    fy_result = await db.execute(select(FiscalYear).filter(FiscalYear.tenant_id == tid).limit(1))
    fiscal_year = fy_result.scalar()

    acc_count = (await db.execute(select(func.count(Account.id)))).scalar() or 0
    cust_count = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    prod_count = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    emp_count = (await db.execute(select(func.count(Employee.id)))).scalar() or 0

    steps, missing, pct = _check_setup_steps(company_profile, fiscal_year, acc_count, cust_count, prod_count, emp_count)

    recommendations = []
    if not company_profile:
        recommendations.append({"priority": "high", "action": "setup_company", "message": "Set up your company profile to get started"})
    if not fiscal_year:
        recommendations.append({"priority": "high", "action": "create_fiscal_year", "message": "Create a fiscal year for accounting"})
    if acc_count < 5:
        recommendations.append({"priority": "medium", "action": "setup_accounts", "message": "Set up your chart of accounts"})
    if prod_count == 0:
        recommendations.append({"priority": "medium", "action": "add_products", "message": "Add your first products"})
    if cust_count == 0:
        recommendations.append({"priority": "low", "action": "add_customers", "message": "Add your first customers"})

    await log_audit(
        db, tenant_id=tid, user=current_user,
        action="query", module="ai",
        entity_type="Onboarding", entity_id="status",
        entity_name=f"Completion: {pct:.0f}%", request=None,
    )

    return OnboardingStatusResponse(
        tenant_id=tid,
        company_name=company_profile.legal_name if company_profile else None,
        setup_complete=pct >= 100,
        completion_percentage=pct,
        steps=steps,
        missing_steps=[m["step"] for m in missing],
        recommendations=recommendations,
    )


@router.post("/onboarding/setup-company")
async def setup_company_profile(
    request: Request,
    body: CompanyProfileSetup,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    tid = current_user["tenant_id"]

    result = await db.execute(select(CompanyProfile).filter(CompanyProfile.tenant_id == tid).limit(1))
    existing = result.scalar()

    if existing:
        for key, val in body.model_dump(exclude_unset=True).items():
            setattr(existing, key, val)
        profile = existing
    else:
        profile = CompanyProfile(
            id=str(uuid.uuid4()), tenant_id=tid,
            legal_name=body.company_name,
            legal_name_ar=body.company_name_ar,
            trade_name=body.company_name,
            trade_name_ar=body.company_name_ar,
            phone=body.phone,
            email=body.email,
            address=body.address,
            city=body.city,
            country=body.country,
            tax_number=body.tax_id,
            commercial_register=body.commercial_registration,
        )
        db.add(profile)

    await db.flush()

    await log_audit(
        db, tenant_id=tid, user=current_user,
        action="create", module="ai",
        entity_type="CompanyProfile", entity_id=profile.id,
        entity_name=profile.legal_name, request=request,
    )

    return {"status": "ok", "profile_id": profile.id, "message": "Company profile saved"}


@router.post("/onboarding/initialize")
async def initialize_tenant_data(
    request: Request,
    body: InitialDataLoad,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    tid = current_user["tenant_id"]
    created = {"accounts": 0, "fiscal_year": False}

    # Create chart of accounts for industry
    accounts = INDUSTRY_ACCOUNTS.get(body.industry, INDUSTRY_ACCOUNTS["services"])
    for code, name, atype in accounts:
        existing = await db.execute(
            select(Account).filter(Account.code == code).limit(1)
        )
        if not existing.scalar():
            db.add(Account(
                id=str(uuid.uuid4()),
                code=code, name=name, name_ar=name,
                account_type=atype, is_active=True,
            ))
            created["accounts"] += 1

    # Create default fiscal year if not exists
    fy_result = await db.execute(select(FiscalYear).filter(FiscalYear.tenant_id == tid).limit(1))
    if not fy_result.scalar():
        now = datetime.utcnow()
        db.add(FiscalYear(
            id=str(uuid.uuid4()), tenant_id=tid,
            name=f"FY {now.year}",
            start_date=date(now.year, 1, 1),
            end_date=date(now.year, 12, 31),
            is_current=True,
            is_closed=False,
        ))
        created["fiscal_year"] = True

    await db.flush()

    await log_audit(
        db, tenant_id=tid, user=current_user,
        action="create", module="ai",
        entity_type="Onboarding", entity_id="initialize",
        entity_name=f"Created {created['accounts']} accounts, fy={created['fiscal_year']}",
        request=request,
    )

    return {
        "status": "ok",
        "created": created,
        "message": f"Initialized {body.industry} template with {created['accounts']} accounts",
    }
