"""
P58 Migration — SaaS Journeys (orchestrated signup→ERP)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text


def migrate():
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_saas_journeys ("
            "id VARCHAR(36) PRIMARY KEY,"
            "tenant_id VARCHAR(100) NOT NULL,"
            "user_id VARCHAR(100),"
            "company_name VARCHAR(200),"
            "admin_email VARCHAR(200),"
            "business_description TEXT NOT NULL,"
            "detected_industry VARCHAR(50),"
            "composer_session_id VARCHAR(36),"
            "project_id VARCHAR(36),"
            "plan_code VARCHAR(50),"
            "billing_cycle VARCHAR(20),"
            "invoice_id VARCHAR(36),"
            "license_key VARCHAR(100),"
            "status VARCHAR(30) NOT NULL DEFAULT 'drafted',"
            "steps_data JSONB NOT NULL DEFAULT '{}',"
            "created_at TIMESTAMP DEFAULT NOW(),"
            "updated_at TIMESTAMP DEFAULT NOW())"
        ))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_journey_tenant ON dbp_saas_journeys(tenant_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_journey_status ON dbp_saas_journeys(status)"))
        print("  [OK] dbp_saas_journeys")


if __name__ == "__main__":
    print("=" * 60)
    print("  P58 MIGRATION — SaaS Journeys")
    print("=" * 60)
    migrate()
    print("  DONE")
