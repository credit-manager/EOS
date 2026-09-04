import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

config = context.config

db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models to ensure they are registered with Base.metadata
try:
    import models  # noqa: F401
    from models import Base

    try:
        from core import ai_composer, builder_engine, metadata_engine  # noqa: F401
    except ImportError:
        pass

    target_metadata = Base.metadata
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    target_metadata = None

# These tables are retained for backward compatibility but are no longer part
# of the canonical ORM metadata. They must not be treated as accidental schema
# drift by `alembic check`.
LEGACY_TABLES = {
    "dbp_rate_limits",
    "dbp_accounts",
    "dbp_journal_entries",
    "dbp_journal_lines",
    "number_sequences",
}


def include_object(object_, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and name in LEGACY_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
