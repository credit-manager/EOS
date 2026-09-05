from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context, op
from alembic.ddl.impl import DefaultImpl
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

config = context.config

# Historical EOS migrations were generated against a populated database and
# contain cleanup operations before rebuilding the canonical schema. Make
# those cleanup operations idempotent when the full chain runs on a fresh DB.
_original_drop_index = op.drop_index


def _safe_drop_index(index_name, table_name=None, schema=None, **kw):
    kw.setdefault("if_exists", True)
    return _original_drop_index(index_name, table_name, schema=schema, **kw)


# Patch the Alembic op proxy used directly by generated migration modules.
op.drop_index = _safe_drop_index

# Alembic 1.12's Operations.drop_table() does not expose an if_exists
# argument. Passing one is interpreted as a dialect-specific table option
# and eventually emits a plain DROP TABLE, which fails on a clean database.
# Patch the low-level implementation instead so every generated
# op.drop_table() remains source-compatible while becoming idempotent.
_original_impl_drop_table = DefaultImpl.drop_table


def _safe_impl_drop_table(self, table, **kw):
    preparer = self.dialect.identifier_preparer
    qualified_name = preparer.format_table(table)
    return self._exec(text(f"DROP TABLE IF EXISTS {qualified_name} CASCADE"))


DefaultImpl.drop_table = _safe_impl_drop_table

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
