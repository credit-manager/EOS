"""
P13 Migration: Advanced Security & Governance
- Adds security columns to dbp_fields
- Creates dbp_row_rules table
"""
from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    db = SessionLocal()
    try:
        # Add security columns to dbp_fields (safe for existing data)
        for col_name, col_def in [
            ("is_sensitive", "BOOLEAN DEFAULT false"),
            ("writable_roles", "JSONB DEFAULT '[]'"),
            ("visible_roles", "JSONB DEFAULT '[]'"),
            ("validation_rules", "JSONB DEFAULT '{}'"),
        ]:
            try:
                db.execute(text(
                    f"ALTER TABLE dbp_fields ADD COLUMN {col_name} {col_def}"
                ))
                print(f"  Added {col_name} to dbp_fields")
            except Exception:
                print(f"  {col_name} already exists on dbp_fields")

        # Create dbp_row_rules table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_row_rules (
                id VARCHAR(36) PRIMARY KEY,
                entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
                filter_column VARCHAR(100) NOT NULL,
                filter_type VARCHAR(20) NOT NULL DEFAULT 'equals',
                filter_value VARCHAR(500),
                allowed_roles JSONB DEFAULT '[]',
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_row_rules_entity ON dbp_row_rules (entity_id)"
        ))

        db.commit()
        print("P13 migration complete")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
