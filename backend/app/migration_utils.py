import logging
from pathlib import Path

from alembic import command, config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

logger = logging.getLogger("2to-eos.migrations")


def get_alembic_config(database_url: str) -> config.Config:
    alembic_cfg = config.Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    return alembic_cfg


def run_migrations(database_url: str) -> bool:
    try:
        alembic_cfg = get_alembic_config(database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully for %s", database_url)
        return True
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        return False


def rollback_migrations(database_url: str, revision: str = "base") -> bool:
    try:
        alembic_cfg = get_alembic_config(database_url)
        command.downgrade(alembic_cfg, revision)
        logger.info("Rollback to %s completed for %s", revision, database_url)
        return True
    except Exception as exc:
        logger.error("Rollback failed: %s", exc)
        return False


def get_current_revision(database_url: str) -> str | None:
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    except Exception as exc:
        logger.error("Failed to get current revision: %s", exc)
        return None


def get_pending_migrations(database_url: str) -> list[str]:
    try:
        alembic_cfg = get_alembic_config(database_url)
        script_directory = command.script_directory(alembic_cfg)
        
        current = get_current_revision(database_url)
        
        revisions = []
        for revision in script_directory.walk_revisions():
            if current and revision.revision == current:
                break
            revisions.append(revision.revision)
        
        return revisions
    except Exception as exc:
        logger.error("Failed to get pending migrations: %s", exc)
        return []


def verify_migration_integrity(database_url: str) -> dict:
    result = {
        "database_url": database_url.split("@")[-1] if "@" in database_url else database_url,
        "current_revision": None,
        "pending_migrations": [],
        "tables": [],
        "is_valid": False,
    }
    
    try:
        result["current_revision"] = get_current_revision(database_url)
        result["pending_migrations"] = get_pending_migrations(database_url)
        
        engine = create_engine(database_url)
        inspector = inspect(engine)
        result["tables"] = inspector.get_table_names()
        
        result["is_valid"] = len(result["pending_migrations"]) == 0
        
    except Exception as exc:
        logger.error("Migration verification failed: %s", exc)
        result["error"] = str(exc)
    
    return result
