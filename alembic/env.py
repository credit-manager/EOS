from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context, op
from alembic.operations import Operations
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

config = context.config

# Historical EOS migrations were generated against a populated database and
# contain cleanup operations before rebuilding the canonical schema. Make
# those cleanup operations idempotent when the full chain runs on a fresh DB.
_original_drop_index = op.drop_index
_original_drop_table = op.drop_table


def _safe_drop_index(index_name, table_name=None, schema=None, **kw):
    kw.setdefault("if_exists", True)
    return _original_drop_index(index_name, table_name, schema=schema, **kw)


def _safe_drop_table(table_name, schema=None, **kw):
    kw.setdefault("if_exists", True)
    return _original_drop_table(table_name, schema=schema, **kw)


# Patch the Alembic op proxy used directly by generated migration modules.
op.drop_index = _safe_drop_index
op.drop_table = _safe_drop_table

# Keep Operations patched as well for migrations that invoke the class API.
_operations_drop_index = Operations.drop_index
_operations_drop_table = Operations.drop_table


def _safe_operations_drop_index(self, index_name, table_name=None, schema=None, **kw):
    kw.setdefault("if_exists", True)
    return _operations_drop_index(self, index_name, table_name, schema=schema, **kw)


def _safe_operations_drop_table(self, table_name, schema=None, **kw):
    kw.setdefault("if_exists", True)
    return _operations_drop_table(self, table_name, schema=schema, **kw)


Operations.drop_index = _safe_operations_drop_index
Operations.drop_table = _safe_operations_drop_table

db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models to ensure they are registered with Base.metadata
try:
    from models import Base
    import models  # noqa: F401
    try:
        from core import builder_engine, ai_composer, metadata_engine  # noqa: F401
    except ImportError:
        pass
    target_metadata = Base.metadata
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
