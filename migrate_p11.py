"""P11 Migration: Create dbp_entity_versions table."""
from database import engine, SessionLocal
from sqlalchemy import text
from models import DBPEntity, DBPField
from core.versioning_engine import VersioningEngine
import uuid


def migrate():
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_entity_versions (
                id VARCHAR(36) PRIMARY KEY,
                entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL,
                schema_snapshot JSONB NOT NULL,
                change_type VARCHAR(50) NOT NULL,
                changed_by VARCHAR(100) NOT NULL,
                changed_at TIMESTAMPTZ DEFAULT NOW(),
                change_summary TEXT
            )
        """))

        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_entity_versions_entity_id "
            "ON dbp_entity_versions (entity_id)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_entity_versions_entity_version "
            "ON dbp_entity_versions (entity_id, version_number)"
        ))
        db.commit()

        existing_count = db.execute(
            text("SELECT COUNT(*) FROM dbp_entity_versions")
        ).scalar()

        if existing_count == 0:
            print("Backfilling initial versions for existing entities...")
            ve = VersioningEngine(db)
            entities = db.query(DBPEntity).all()
            for entity in entities:
                ve.create_version(
                    entity_id=entity.id,
                    change_type="initial",
                    changed_by="migration_p11",
                    change_summary="Initial version snapshot",
                )
            db.commit()
            print(f"  Backfilled {len(entities)} entity versions")
        else:
            print(f"  {existing_count} versions already exist, skipping backfill")

        print("P11 migration complete")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
