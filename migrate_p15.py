"""
P15 Notification & Communication — Migration
Creates dbp_notifications, dbp_notification_templates, dbp_notification_preferences
"""
from sqlalchemy import text
from database import engine


def migrate_p15():
    with engine.begin() as conn:
        # Notifications
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_notifications (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                user_id VARCHAR(100) NOT NULL,
                channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
                title VARCHAR(500) NOT NULL,
                message TEXT,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'info',
                entity_code VARCHAR(100),
                record_id VARCHAR(36),
                event_id VARCHAR(36),
                action_url VARCHAR(500),
                is_read BOOLEAN DEFAULT false,
                read_at TIMESTAMPTZ,
                extra_data JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_notifications")

        # Indexes for notifications
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_notif_tenant ON dbp_notifications(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_notif_user ON dbp_notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_notif_channel ON dbp_notifications(channel)",
            "CREATE INDEX IF NOT EXISTS idx_notif_type ON dbp_notifications(notification_type)",
            "CREATE INDEX IF NOT EXISTS idx_notif_read ON dbp_notifications(is_read)",
            "CREATE INDEX IF NOT EXISTS idx_notif_created ON dbp_notifications(created_at DESC)",
        ]:
            conn.execute(text(idx_sql))

        # Templates
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_notification_templates (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                code VARCHAR(100) NOT NULL,
                channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
                notification_type VARCHAR(50) NOT NULL DEFAULT 'info',
                title_template VARCHAR(500) NOT NULL,
                message_template TEXT,
                event_type VARCHAR(50) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_notification_templates")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tmpl_code "
            "ON dbp_notification_templates(code)"
        ))

        # Preferences
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_notification_preferences (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                user_id VARCHAR(100) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
                is_enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_notification_preferences")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_pref_user_type_channel "
            "ON dbp_notification_preferences(user_id, notification_type, channel)"
        ))

    print("\nP15 migration complete.")


if __name__ == "__main__":
    print("Running P15 migration...")
    migrate_p15()
