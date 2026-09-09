"""
P61 Migration — Production Authentication
Tables: dbp_users
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_users": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("email", "VARCHAR(255) NOT NULL"),
        ("password_hash", "VARCHAR(255) NOT NULL"),
        ("first_name", "VARCHAR(100) NOT NULL"),
        ("last_name", "VARCHAR(100) NOT NULL"),
        ("first_name_ar", "VARCHAR(100)"),
        ("last_name_ar", "VARCHAR(100)"),
        ("phone", "VARCHAR(50)"),
        ("role", "VARCHAR(50) NOT NULL DEFAULT 'admin'"),
        ("is_active", "BOOLEAN NOT NULL DEFAULT true"),
        ("email_verified", "BOOLEAN NOT NULL DEFAULT false"),
        ("verification_token_hash", "VARCHAR(255)"),
        ("verification_expires_at", "TIMESTAMP"),
        ("reset_token_hash", "VARCHAR(255)"),
        ("reset_expires_at", "TIMESTAMP"),
        ("last_login_at", "TIMESTAMP"),
        ("failed_login_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
        ("updated_at", "TIMESTAMP DEFAULT NOW()"),
    ],
}

INDICES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON dbp_users(email)",
    "CREATE INDEX IF NOT EXISTS idx_users_tenant ON dbp_users(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_users_tenant_email ON dbp_users(tenant_id, email)",
    "CREATE INDEX IF NOT EXISTS idx_users_verification_hash ON dbp_users(verification_token_hash)",
    "CREATE INDEX IF NOT EXISTS idx_users_reset_hash ON dbp_users(reset_token_hash)",
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
    print("  P61 MIGRATION — Production Authentication")
    print("=" * 60)
    migrate()
    print("  DONE")
