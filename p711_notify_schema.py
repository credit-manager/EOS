"""
P71.1 Shared Notification Engine — Database Schema
====================================================
Event-driven notification system shared across all industries.
Fires events → matches rules → delivers via channels (in-app, email).
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from database import engine
from sqlalchemy import text

TABLES = [
    # ─── Event Log ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_events (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        source_module VARCHAR(50) NOT NULL,
        source_id VARCHAR(36),
        payload JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Notification Rules ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_rules (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        rule_name VARCHAR(200) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        source_module VARCHAR(50),
        channel VARCHAR(30) NOT NULL,
        recipient_type VARCHAR(30) NOT NULL,
        recipient_value VARCHAR(200),
        template_id VARCHAR(36),
        is_active BOOLEAN DEFAULT TRUE,
        priority INTEGER DEFAULT 5,
        conditions JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Notification Templates ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_templates (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        template_code VARCHAR(100) NOT NULL,
        name VARCHAR(200) NOT NULL,
        channel VARCHAR(30) NOT NULL,
        subject VARCHAR(500),
        body TEXT NOT NULL,
        body_html TEXT,
        variables JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Inbox (In-App Notifications) ──────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_inbox (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        event_id VARCHAR(36),
        title VARCHAR(500) NOT NULL,
        body TEXT,
        link VARCHAR(500),
        category VARCHAR(50) DEFAULT 'info',
        is_read BOOLEAN DEFAULT FALSE,
        read_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Channel Config ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_channels (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        channel VARCHAR(30) NOT NULL,
        config JSONB NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── User Preferences ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_notify_preferences (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        category VARCHAR(50) NOT NULL,
        in_app BOOLEAN DEFAULT TRUE,
        email BOOLEAN DEFAULT FALSE,
        is_muted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_notify_events_tenant ON dbp_notify_events(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_events_type ON dbp_notify_events(tenant_id, event_type)",
    "CREATE INDEX IF NOT EXISTS idx_notify_events_source ON dbp_notify_events(source_module, source_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_events_created ON dbp_notify_events(tenant_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_notify_rules_tenant ON dbp_notify_rules(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_rules_event ON dbp_notify_rules(tenant_id, event_type)",
    "CREATE INDEX IF NOT EXISTS idx_notify_rules_active ON dbp_notify_rules(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_notify_templates_tenant ON dbp_notify_templates(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_templates_code ON dbp_notify_templates(tenant_id, template_code)",
    "CREATE INDEX IF NOT EXISTS idx_notify_inbox_tenant ON dbp_notify_inbox(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_inbox_user ON dbp_notify_inbox(user_id, is_read)",
    "CREATE INDEX IF NOT EXISTS idx_notify_inbox_created ON dbp_notify_inbox(tenant_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_notify_channels_tenant ON dbp_notify_channels(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_prefs_tenant ON dbp_notify_preferences(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_notify_prefs_user ON dbp_notify_preferences(user_id)",
]

UNIQUES = [
    "ALTER TABLE dbp_notify_rules ADD CONSTRAINT uq_notify_rule UNIQUE (tenant_id, rule_name)",
    "ALTER TABLE dbp_notify_templates ADD CONSTRAINT uq_notify_template UNIQUE (tenant_id, template_code)",
    "ALTER TABLE dbp_notify_channels ADD CONSTRAINT uq_notify_channel UNIQUE (tenant_id, channel)",
    "ALTER TABLE dbp_notify_preferences ADD CONSTRAINT uq_notify_pref UNIQUE (tenant_id, user_id, category)",
]

CHECKS = [
    "ALTER TABLE dbp_notify_rules ADD CONSTRAINT chk_notify_rule_channel CHECK (channel IN ('in_app','email','sms','whatsapp'))",
    "ALTER TABLE dbp_notify_rules ADD CONSTRAINT chk_notify_rule_recipient CHECK (recipient_type IN ('user','role','manager','all','assigned'))",
    "ALTER TABLE dbp_notify_templates ADD CONSTRAINT chk_notify_template_channel CHECK (channel IN ('in_app','email','sms','whatsapp'))",
    "ALTER TABLE dbp_notify_inbox ADD CONSTRAINT chk_notify_inbox_category CHECK (category IN ('info','success','warning','error','approval','task','system'))",
    "ALTER TABLE dbp_notify_channels ADD CONSTRAINT chk_notify_channel_name CHECK (channel IN ('in_app','email','sms','whatsapp'))",
]

DEFAULTS = [
    "ALTER TABLE dbp_notify_rules ALTER COLUMN is_active SET DEFAULT TRUE",
    "ALTER TABLE dbp_notify_rules ALTER COLUMN priority SET DEFAULT 5",
    "ALTER TABLE dbp_notify_templates ALTER COLUMN is_active SET DEFAULT TRUE",
    "ALTER TABLE dbp_notify_inbox ALTER COLUMN is_read SET DEFAULT FALSE",
    "ALTER TABLE dbp_notify_inbox ALTER COLUMN category SET DEFAULT 'info'",
    "ALTER TABLE dbp_notify_channels ALTER COLUMN is_active SET DEFAULT TRUE",
    "ALTER TABLE dbp_notify_preferences ALTER COLUMN in_app SET DEFAULT TRUE",
    "ALTER TABLE dbp_notify_preferences ALTER COLUMN email SET DEFAULT FALSE",
    "ALTER TABLE dbp_notify_preferences ALTER COLUMN is_muted SET DEFAULT FALSE",
]


def migrate():
    with engine.begin() as conn:
        created = sum(1 for sql in TABLES if not _exec(conn, sql.strip()))
        idx = sum(1 for sql in INDEXES if not _exec(conn, sql))
        uq = sum(1 for sql in UNIQUES if not _exec(conn, sql))
        chk = sum(1 for sql in CHECKS if not _exec(conn, sql))
        df = sum(1 for sql in DEFAULTS if not _exec(conn, sql))
    print(f"P71.1 Notification Engine Schema: {created} tables, {idx} indexes, {uq} uniques, {chk} checks, {df} defaults")


def _exec(conn, sql):
    try:
        conn.execute(text(sql))
        return False
    except Exception:
        return True


if __name__ == "__main__":
    migrate()
