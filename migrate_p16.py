"""
P16 Dashboard / Analytics — Migration
Creates dbp_dashboards, dbp_dashboard_widgets, dbp_kpis
"""
from sqlalchemy import text
from database import engine


def migrate_p16():
    with engine.begin() as conn:
        # Dashboards
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_dashboards (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                code VARCHAR(100) NOT NULL,
                name_en VARCHAR(255) NOT NULL,
                name_ar VARCHAR(255),
                description TEXT,
                layout JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT true,
                is_default BOOLEAN DEFAULT false,
                owner_user_id VARCHAR(100),
                allowed_roles JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """))
        print("  [OK] dbp_dashboards")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_dash_code "
            "ON dbp_dashboards(code)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_dash_tenant ON dbp_dashboards(tenant_id)"
        ))

        # Widgets
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_dashboard_widgets (
                id VARCHAR(36) PRIMARY KEY,
                dashboard_id VARCHAR(36) NOT NULL REFERENCES dbp_dashboards(id) ON DELETE CASCADE,
                code VARCHAR(100) NOT NULL,
                widget_type VARCHAR(50) NOT NULL DEFAULT 'kpi',
                title VARCHAR(255) NOT NULL,
                title_ar VARCHAR(255),
                entity_code VARCHAR(100) NOT NULL,
                position_x INTEGER DEFAULT 0,
                position_y INTEGER DEFAULT 0,
                width INTEGER DEFAULT 1,
                height INTEGER DEFAULT 1,
                query_config JSONB DEFAULT '{}',
                style_config JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_dashboard_widgets")

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_widget_dash "
            "ON dbp_dashboard_widgets(dashboard_id)"
        ))

        # KPIs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_kpis (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                code VARCHAR(100) NOT NULL,
                name_en VARCHAR(255) NOT NULL,
                name_ar VARCHAR(255),
                entity_code VARCHAR(100) NOT NULL,
                aggregation VARCHAR(20) NOT NULL,
                column_name VARCHAR(100),
                filters JSONB DEFAULT '[]',
                group_by VARCHAR(100),
                date_field VARCHAR(100),
                date_range VARCHAR(20),
                format_type VARCHAR(20) DEFAULT 'number',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_kpis")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_kpi_code "
            "ON dbp_kpis(code)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_kpi_tenant ON dbp_kpis(tenant_id)"
        ))

    print("\nP16 migration complete.")


if __name__ == "__main__":
    print("Running P16 migration...")
    migrate_p16()
