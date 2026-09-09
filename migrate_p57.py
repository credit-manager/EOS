"""
P57 Migration — Customer Portal support tickets
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text


def migrate():
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS dbp_support_tickets ("
            "id VARCHAR(36) PRIMARY KEY,"
            "tenant_id VARCHAR(100) NOT NULL,"
            "ticket_number VARCHAR(30) NOT NULL,"
            "subject VARCHAR(300) NOT NULL,"
            "message TEXT,"
            "priority VARCHAR(20) NOT NULL DEFAULT 'normal',"
            "status VARCHAR(20) NOT NULL DEFAULT 'open',"
            "created_by VARCHAR(100),"
            "created_at TIMESTAMP DEFAULT NOW(),"
            "resolved_at TIMESTAMP)"
        ))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_supp_tenant ON dbp_support_tickets(tenant_id)"))
        print("  [OK] dbp_support_tickets")


if __name__ == "__main__":
    print("=" * 60)
    print("  P57 MIGRATION — Customer Portal")
    print("=" * 60)
    migrate()
    print("  DONE")
