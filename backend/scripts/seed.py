"""Production seed script — creates plans, super admin, and demo tenant."""
import json
import sys
import uuid
from datetime import datetime, UTC, timedelta

from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.auth.models import Tenant, User, TenantMembership
from app.billing.models import Plan, Subscription, Invoice
from app.billing.seed import PLANS
from app.feature_flags.models import FeatureFlag
from app.notification.models import Notification
from app.auth.security import hash_password

DEFAULT_FEATURE_FLAGS = [
    {"code": "erp_module", "name": "ERP Module", "description": "Core ERP functionality", "is_global": True},
    {"code": "ai_workforce", "name": "AI Workforce", "description": "AI agents and copilots", "is_global": True},
    {"code": "automation", "name": "Automation", "description": "Workflow automation engine", "is_global": True},
    {"code": "advanced_analytics", "name": "Advanced Analytics", "description": "Advanced reporting and BI", "is_global": False, "enabled_plans": ["professional", "enterprise"]},
    {"code": "industry_os", "name": "Industry OS", "description": "Industry-specific modules", "is_global": False, "enabled_plans": ["professional", "enterprise"]},
    {"code": "api_access", "name": "API Access", "description": "Public API access", "is_global": True},
    {"code": "sso", "name": "SSO", "description": "Single Sign-On", "is_global": False, "enabled_plans": ["enterprise"]},
    {"code": "custom_objects", "name": "Custom Objects", "description": "Builder custom objects", "is_global": False, "enabled_plans": ["enterprise"]},
]


def seed_plans(db: Session) -> int:
    count = 0
    for plan_data in PLANS:
        existing = db.query(Plan).filter(Plan.code == plan_data["code"]).first()
        if not existing:
            plan = Plan(
                id=str(uuid.uuid4()),
                code=plan_data["code"],
                name=plan_data["name"],
                description=plan_data.get("description", ""),
                price_monthly=plan_data["price_monthly"],
                price_yearly=plan_data.get("price_yearly"),
                max_users=plan_data.get("max_users", 10),
                max_storage_gb=plan_data.get("max_storage_gb", 5),
                features=plan_data.get("features", "[]"),
                is_active=True,
            )
            db.add(plan)
            count += 1
    db.commit()
    return count


def seed_super_admin(db: Session) -> User | None:
    existing = db.query(User).filter(User.email == "admin@2to-eos.local").first()
    if existing:
        return existing
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    admin = User(
        id=user_id,
        email="admin@2to-eos.local",
        password_hash=hash_password("CHANGE_ME_IN_PRODUCTION"),
        is_active=True,
        risk_status="low",
        mfa_enabled=False,
    )
    db.add(admin)
    db.flush()

    tenant = Tenant(
        id=tenant_id,
        name="2TO EOS Platform",
        industry="Technology",
        country="SA",
        plan="enterprise",
        status="active",
        storage_gb=0,
        ai_usage_pct=0,
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        role="super_admin",
    )
    db.add(membership)
    db.commit()
    print(f"  Super admin: admin@2to-eos.local (tenant: {tenant.name})")
    return admin


def seed_demo_tenant(db: Session) -> Tenant | None:
    existing = db.query(Tenant).filter(Tenant.name == "Acme Corp").first()
    if existing:
        return existing

    starter = db.query(Plan).filter(Plan.code == "starter").first()
    plan_id = starter.id if starter else ""

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = Tenant(
        id=tenant_id,
        name="Acme Corp",
        industry="Technology",
        country="SA",
        plan="starter",
        status="active",
        storage_gb=2,
        ai_usage_pct=15,
        is_active=True,
    )
    db.add(tenant)
    db.flush()

    demo_user = User(
        id=user_id,
        email="demo@acme.com",
        password_hash=hash_password("demo12345"),
        is_active=True,
        risk_status="low",
        mfa_enabled=False,
    )
    db.add(demo_user)
    db.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        role="admin",
    )
    db.add(membership)

    if plan_id:
        sub = Subscription(
            id=str(uuid.uuid4()),
            tenant_id=str(tenant_id),
            plan_id=plan_id,
            status="active",
            billing_cycle="monthly",
            current_period_start=datetime.now(UTC),
            current_period_end=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(sub)

    db.commit()
    print(f"  Demo tenant: Acme Corp (user: demo@acme.com)")
    return tenant


def seed_feature_flags(db: Session) -> int:
    count = 0
    for flag_data in DEFAULT_FEATURE_FLAGS:
        existing = db.query(FeatureFlag).filter(FeatureFlag.code == flag_data["code"]).first()
        if not existing:
            flag = FeatureFlag(
                id=str(uuid.uuid4()),
                code=flag_data["code"],
                name=flag_data["name"],
                description=flag_data.get("description", ""),
                is_global=flag_data.get("is_global", False),
                enabled_plans=json.dumps(flag_data.get("enabled_plans", [])),
                enabled_tenants="[]",
                is_active=True,
            )
            db.add(flag)
            count += 1
    db.commit()
    return count


def run_seed():
    print("=" * 60)
    print("  2TO EOS — Database Seed")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("\n1. Seeding billing plans...")
        plans = seed_plans(db)
        print(f"   {plans} plan(s) created")

        print("\n2. Creating super admin...")
        seed_super_admin(db)

        print("\n3. Creating demo tenant...")
        seed_demo_tenant(db)

        print("\n4. Seeding feature flags...")
        flags = seed_feature_flags(db)
        print(f"   {flags} flag(s) created")

        print("\n" + "=" * 60)
        print("  Seed complete!")
        print("=" * 60)
        print("\nLogin credentials:")
        print("  Super Admin: admin@2to-eos.local / CHANGE_ME_IN_PRODUCTION")
        print("  Demo User:   demo@acme.com / demo12345")
    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
