"""Default billing plans for seeding."""
PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "For small teams getting started",
        "price_monthly": 49,
        "max_users": 5,
        "max_storage_gb": 5,
        "features": '["basic_modules","5GB_storage","email_support"]',
    },
    {
        "code": "professional",
        "name": "Professional",
        "description": "For growing businesses",
        "price_monthly": 149,
        "price_yearly": 1490,
        "max_users": 25,
        "max_storage_gb": 50,
        "features": '["all_modules","50GB_storage","ai_copilot","priority_support","sso"]',
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "For large-scale operations",
        "price_monthly": 499,
        "price_yearly": 4990,
        "max_users": -1,
        "max_storage_gb": -1,
        "features": '["all_modules","unlimited_storage","ai_copilot","24x7_support","sso","custom_objects","api_access","audit_trail"]',
    },
]
