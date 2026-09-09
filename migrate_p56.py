"""
P56 Migration — seed commercial plan catalog into dbp_saas_plans
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

PLANS = [
    {"code": "starter", "name": "Starter", "m": 99, "y": 990, "users": 5,
     "companies": 1, "storage": 5,
     "features": ["accounting", "finance", "sales", "inventory"]},
    {"code": "professional", "name": "Professional", "m": 299, "y": 2990, "users": 25,
     "companies": 3, "storage": 50,
     "features": ["accounting", "finance", "sales", "inventory", "procurement",
                   "projects", "hr", "documents", "workflow"]},
    {"code": "business", "name": "Business", "m": 699, "y": 6990, "users": 100,
     "companies": 10, "storage": 200,
     "features": ["accounting", "finance", "sales", "inventory", "procurement",
                   "projects", "hr", "documents", "workflow", "fixed_assets",
                   "audit", "bi"]},
    {"code": "enterprise", "name": "Enterprise", "m": 1999, "y": 19990, "users": 1000,
     "companies": 100, "storage": 1000,
     "features": ["all_modules", "sso", "api_access", "priority_support",
                   "custom_builder", "marketplace_all"]},
]


def migrate():
    import uuid
    with engine.begin() as conn:
        for p in PLANS:
            exists = conn.execute(text("SELECT id FROM dbp_saas_plans WHERE plan_code=:c"),
                                   {"c": p["code"]}).fetchone()
            if exists:
                continue
            conn.execute(text(
                "INSERT INTO dbp_saas_plans "
                "(id, tenant_id, plan_name, plan_code, price_monthly, price_yearly, "
                "max_users, max_companies, max_storage_gb, features, is_active) "
                "VALUES (:id, 'platform', :n, :c, :m, :y, :u, :co, :st, CAST(:f AS JSONB), true)"
            ), {"id": str(uuid.uuid4()), "n": p["name"], "c": p["code"],
                "m": p["m"], "y": p["y"], "u": p["users"], "co": p["companies"],
                "st": p["storage"], "f": json.dumps(p["features"])})
        print(f"  [OK] Seeded {len(PLANS)} plans")


if __name__ == "__main__":
    print("=" * 60)
    print("  P56 MIGRATION — Plan Catalog")
    print("=" * 60)
    migrate()
    print("  DONE")
