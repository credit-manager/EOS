"""P12 Migration: Create dbp_events, dbp_webhooks, dbp_webhook_deliveries tables."""
from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_events (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                event_type VARCHAR(50) NOT NULL,
                entity_code VARCHAR(100) NOT NULL,
                record_id VARCHAR(36),
                user_id VARCHAR(100),
                payload JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_events_entity_code ON dbp_events (entity_code)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_events_event_type ON dbp_events (event_type)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_events_tenant ON dbp_events (tenant_id)"
        ))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_webhooks (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                code VARCHAR(100) UNIQUE NOT NULL,
                target_url VARCHAR(500) NOT NULL,
                entity_code VARCHAR(100) NOT NULL,
                event_types JSONB NOT NULL DEFAULT '[]',
                secret VARCHAR(200),
                is_active BOOLEAN DEFAULT true,
                custom_headers JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_webhooks_entity ON dbp_webhooks (entity_code)"
        ))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_webhook_deliveries (
                id VARCHAR(36) PRIMARY KEY,
                webhook_id VARCHAR(36) NOT NULL REFERENCES dbp_webhooks(id) ON DELETE CASCADE,
                event_id VARCHAR(36) NOT NULL REFERENCES dbp_events(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                last_response_code INTEGER,
                last_error TEXT,
                next_retry_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_deliveries_webhook ON dbp_webhook_deliveries (webhook_id)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_deliveries_status ON dbp_webhook_deliveries (status)"
        ))
        db.commit()

        print("P12 migration complete")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
