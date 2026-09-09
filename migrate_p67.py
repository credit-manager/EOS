"""
P67 Migration — White-Label SaaS
Tables: dbp_tenant_branding

One branding row per tenant (unique tenant_id), covering:
  - Identity: system name (en/ar), logo, favicon
  - Theme: primary/secondary colors, mode, direction
  - Login page texts
  - Email & report header/footer
  - Custom domain + verification state
  - White-label feature flags (powered-by visibility etc.)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_tenant_branding": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        # Identity
        ("system_name_en", "VARCHAR(120)"),
        ("system_name_ar", "VARCHAR(120)"),
        ("logo_url", "TEXT"),
        ("favicon_url", "TEXT"),
        # Theme
        ("primary_color", "VARCHAR(20) DEFAULT '#1890ff'"),
        ("secondary_color", "VARCHAR(20) DEFAULT '#001529'"),
        ("theme_mode", "VARCHAR(10) DEFAULT 'light'"),      # light | dark
        ("direction", "VARCHAR(5) DEFAULT 'rtl'"),          # rtl | ltr
        # Login branding
        ("login_title_en", "VARCHAR(200)"),
        ("login_title_ar", "VARCHAR(200)"),
        ("login_subtitle_en", "VARCHAR(300)"),
        ("login_subtitle_ar", "VARCHAR(300)"),
        # Communications / documents
        ("email_footer_text", "TEXT"),
        ("report_header_text", "TEXT"),
        ("report_footer_text", "TEXT"),
        # Custom domain
        ("custom_domain", "VARCHAR(255)"),
        ("domain_verified", "BOOLEAN DEFAULT FALSE"),
        ("dns_txt_record", "VARCHAR(255)"),
        # White-label feature control
        ("show_powered_by", "BOOLEAN DEFAULT TRUE"),
        ("enable_custom_domain", "BOOLEAN DEFAULT FALSE"),
        ("enable_custom_branding", "BOOLEAN DEFAULT FALSE"),
        ("enable_custom_login", "BOOLEAN DEFAULT FALSE"),
        # Meta
        ("created_at", "TIMESTAMPTZ DEFAULT NOW()"),
        ("updated_at", "TIMESTAMPTZ DEFAULT NOW()"),
    ],
}

INDICES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_branding_tenant ON dbp_tenant_branding(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_branding_domain ON dbp_tenant_branding(custom_domain)",
]


def migrate():
    with engine.begin() as conn:
        for tbl, cols in TABLES.items():
            col_sql = ", ".join(f"{c[0]} {c[1]}" for c in cols)
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {tbl} ({col_sql})"))
            print(f"  [OK] {tbl}")
        for idx in INDICES:
            try:
                conn.execute(text(idx))
            except Exception as e:
                print(f"  [WARN] index: {e}")
        print(f"  [OK] indices ensured")


if __name__ == "__main__":
    print("=" * 60)
    print("  P67 MIGRATION — White-Label SaaS")
    print("=" * 60)
    migrate()
    print("  DONE")
