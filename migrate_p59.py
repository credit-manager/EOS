"""
P59 Migration — Production SaaS Ops (monitoring, logs, webhooks)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_saas_metrics": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("metric_name", "VARCHAR(100) NOT NULL"),
        ("metric_value", "NUMERIC(14,4) NOT NULL"),
        ("labels", "JSONB DEFAULT '{}'"),
        ("recorded_at", "TIMESTAMP DEFAULT NOW()"),
    ],
    "dbp_saas_alerts": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("alert_type", "VARCHAR(50) NOT NULL"),
        ("severity", "VARCHAR(20) NOT NULL DEFAULT 'info'"),
        ("message", "TEXT NOT NULL"),
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'"),
        ("resolved_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
    ],
    "dbp_webhook_logs": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("event_type", "VARCHAR(100) NOT NULL"),
        ("target_url", "VARCHAR(500)"),
        ("payload", "JSONB DEFAULT '{}'"),
        ("status_code", "INTEGER"),
        ("delivered_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
    ],
}

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_sm_tenant ON dbp_saas_metrics(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_sm_name ON dbp_saas_metrics(metric_name)",
    "CREATE INDEX IF NOT EXISTS idx_sa_tenant ON dbp_saas_alerts(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_wl_tenant ON dbp_webhook_logs(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_wl_event ON dbp_webhook_logs(event_type)",
]


def migrate():
    with engine.begin() as conn:
        for tbl, cols in TABLES.items():
            col_sql = ", ".join(f"{c[0]} {c[1]}" for c in cols)
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {tbl} ({col_sql})"))
            print(f"  [OK] {tbl}")
        for idx in INDICES:
            conn.execute(text(idx))
        print(f"  [OK] {len(INDICES)} indices")


if __name__ == "__main__":
    print("=" * 60)
    print("  P59 MIGRATION — Production SaaS Ops")
    print("=" * 60)
    migrate()
    print("  DONE")
